import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_genesis_places import import_sample,uid

R=uid("test-release:genesis-sample")
P=uid("entity:hegra")


class NamesIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=import_sample(conn)
            if cls.ids!=import_sample(conn):
                raise AssertionError("non-deterministic import")
            if conn.execute("SELECT count(*) FROM knowledge.legacy_crosswalk WHERE namespace='genesis-0.1'").fetchone()[0]!=3:
                raise AssertionError("crosswalk count")
            if conn.execute("SELECT count(*) FROM knowledge.claim_version WHERE id=ANY(%s)",(cls.ids,)).fetchone()[0]!=6:
                raise AssertionError("duplicate versions")
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,cls.ids))
        cls.client=TestClient(app)

    def get(self,path,params=None,status=200):
        r=self.client.get(path,params=params)
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def test_arabic_diacritic_search(self):
        for q in ("الحجر","الحِجر","الحـجر"):
            r=self.get("/api/v1/search",{"q":q,"lang":"ar","release":str(R)})
            self.assertEqual([(x["entity_id"],x["name"]) for x in r["results"]],[(str(P),"الحِجر")])

    def test_english_search(self):
        r=self.get("/api/v1/search",{"q":"hegra","lang":"en","release":str(R)})
        self.assertEqual(r["results"][0]["entity_id"],str(P))

    def test_entity_and_public_geometry(self):
        r=self.get("/api/v1/entities/"+str(P),{"release":str(R)})
        self.assertEqual({n["name"] for n in r["names"]},{"الحِجر","Hegra / Al-Hijr"})
        self.assertEqual(r["kind"],"Place")
        self.assertFalse(any("verification_status" in n for n in r["names"]))
        m=self.get("/api/v1/map/features",{"bbox":"37,26,39,28","release":str(R)})
        self.assertEqual(len(m["features"]),1)
        self.assertEqual(m["features"][0]["geometry"]["coordinates"],[37.9,26.8])

    def test_release_scope(self):
        self.get("/api/v1/entities/"+str(P),{"release":"40000000-0000-0000-0000-000000000001"},404)
        r=self.get("/api/v1/search",{"q":"الحجر","release":"40000000-0000-0000-0000-000000000001"})
        self.assertEqual(r["results"],[])

    def test_search_validation(self):
        for q in (" ","ـ","َ"):
            self.get("/api/v1/search",{"q":q},422)
        self.assertEqual(self.get("/api/v1/search",{"q":"%","release":str(R)})["results"],[])
        self.assertEqual(self.get("/api/v1/search",{"q":"الحجر","as_of":"550","release":str(R)})["results"],[])

    def test_search_pagination(self):
        first=self.get("/api/v1/search",{"q":"ا","lang":"ar","release":str(R),"limit":1})
        self.assertIsNotNone(first["next_after"])
        second=self.get("/api/v1/search",{"q":"ا","lang":"ar","release":str(R),"limit":1,"after":first["next_after"]})
        self.assertNotEqual(first["results"][0]["version_id"],second["results"][0]["version_id"])

    def test_internal_followup_and_provenance(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],6)
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.evidence WHERE version_id=ANY(%s)",(self.ids,)).fetchone()[0],6)
