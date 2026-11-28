import os
import json
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_geology import load,stage
from pipelines.import_genesis_places import uid

R=uid("test-release:geology")
PRIOR=uid("test-release:snapshots")

class GeologyIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.original=load()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=stage(conn)
            assert len(cls.ids)==56 and cls.ids==stage(conn)
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            assert prior==PRIOR
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(prior,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+cls.ids))
        cls.client=TestClient(app)

    def get(self,params=None):
        r=self.client.get("/api/v1/geology",params=params)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def test_exact_records(self):
        r=self.get()
        self.assertEqual([x["record"] for x in r["records"] if x["type"]=="province"],sorted(self.original["provinces"],key=lambda x:str(x["id"])))
        self.assertEqual([x["record"] for x in r["records"] if x["type"]=="volcano"],sorted(self.original["volcanoes"],key=lambda x:x["id"]))
        self.assertEqual(r["semantics"],"present_reference_not_past_reconstruction")
        self.assertIsNone(next(x["record"]["elevation"] for x in r["records"] if x["type"]=="volcano" and x["record"]["id"]=="231806"))

    def test_spatial_links(self):
        links=self.get()["volcano_provinces"]
        self.assertEqual(links["231050"],[])
        self.assertEqual(links["231806"],[17,18])
        self.assertEqual(len(links),12)

    def test_release_scope(self):
        self.assertEqual(self.get({"release":str(PRIOR)})["records"],[])
        self.assertEqual(self.get({"release":str(PRIOR)})["volcano_provinces"],{})

    def test_review_tasks(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],56)

    def test_invalid_geometry(self):
        item={"type":"province","record":dict(self.original["provinces"][0]),"reference":self.original["reference"],"simplification_deg":0.5}
        item["record"]["ring"]=[[0,0],[1,1],[0,1],[1,0],[0,0]]
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("SELECT knowledge.validate_geology(%s::jsonb)",(json.dumps(item),))
