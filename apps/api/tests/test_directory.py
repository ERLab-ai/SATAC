import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_directory import stage,load
from pipelines.import_genesis_places import uid

R=uid("test-release:directory")
PRIOR=uid("test-release:network-restored")

class DirectoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=stage(conn)
            assert len(cls.ids)==513 and cls.ids==stage(conn)
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            assert prior==PRIOR
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(prior,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+cls.ids))
        cls.client=TestClient(app)

    def get(self,params=None,status=200):
        r=self.client.get("/api/v1/directory",params=params)
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def test_exact_records(self):
        for collection,count in (("historical",190),("modern",323)):
            _,d,records=load(collection)
            rows=self.get({"collection":collection,"release":str(R)})["entries"]
            self.assertEqual(len(rows),count)
            self.assertEqual({str(x["record"]["id"]):x["record"] for x in rows},{str(x["id"]):x for x in records})
            self.assertEqual(len({x["entity_id"] for x in rows}),count)
            self.assertTrue(all(x["region_label"]==(x["record"]["region"] if collection=="historical" else d["regions"][x["record"]["region"]]) for x in rows))
            self.assertTrue(all(len(x["references"])==1 for x in rows))

    def test_search_collection_and_region(self):
        self.assertEqual(len(self.get({"q":"الرياض","collection":"modern","region":"الرياض"})["entries"]),1)
        self.assertEqual(len(self.get({"q":"Riyadh","collection":"modern"})["entries"]),1)
        rows=self.get({"q":"جدة","collection":"historical"})["entries"]
        self.assertTrue(any(x["record"]["id"]=="JUDDA_391E214N_S" for x in rows))
        self.get({"q":"ـ"},422)
        self.assertEqual(self.get({"q":"%"})["entries"],[])

    def test_release_isolation(self):
        self.assertEqual(self.get({"release":str(PRIOR)})["entries"],[])
        self.assertEqual(len(self.get()["entries"]),513)
        self.assertEqual(len(self.client.get("/api/v1/map/features",params={"bbox":"-180,-85,180,85"}).json()["features"]),3)

    def test_internal_tasks_and_crosswalk(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],513)
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.legacy_crosswalk WHERE namespace IN ('directory-historical','directory-modern')").fetchone()[0],513)

    def test_invalid_record(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("""SELECT knowledge.validate_directory('{"collection":"historical","region_label":"x","record":{"id":"x","name":"x","lon":190,"lat":0,"region":"x","kind":"towns","source_certainty":"certain"}}'::jsonb)""")
