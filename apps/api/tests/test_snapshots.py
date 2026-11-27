import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_snapshots import load,stage
from pipelines.import_genesis_places import uid

R=uid("test-release:snapshots")
PRIOR=uid("test-release:routes")

class SnapshotIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,_,cls.original=load()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            ids=stage(conn)
            assert len(ids)==31 and ids==stage(conn)
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            assert prior==PRIOR
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(prior,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+ids))
            cls.ids=ids
        cls.client=TestClient(app)

    def get(self,params=None):
        r=self.client.get("/api/v1/snapshots",params=params)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def test_original_records(self):
        rows=self.get()["snapshots"]
        key=lambda x:(x["year"],x["record"].get("id",""))
        self.assertEqual(sorted(rows,key=key),sorted(self.original,key=key))
        self.assertEqual(len(rows),31)

    def test_exact_year_and_bce(self):
        for y,n in [(-199,4),(600,6),(800,3),(1000,7),(1279,7),(1727,1),(1824,1),(1902,1),(1932,1),(-200,0),(799,0)]:
            self.assertEqual(len(self.get({"as_of":str(y)})["snapshots"]),n)
        self.assertEqual(self.get({"as_of":"1727"})["snapshots"][0]["type"],"milestone")

    def test_release_scope(self):
        self.assertEqual(self.get({"release":str(PRIOR)})["snapshots"],[])

    def test_tasks_and_temporal(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],31)
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.temporal_extent WHERE version_id=ANY(%s) AND start_low=end_high",(self.ids,)).fetchone()[0],31)

    def test_invalid_polygon(self):
        import json
        item=next(x for x in self.original if x["type"]=="territory")
        item=json.loads(json.dumps(item))
        item["record"]["geometry"]={"type":"Polygon","coordinates":[[[0,0],[1,1],[0,1],[1,0],[0,0]]]}
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("SELECT knowledge.validate_snapshot(%s::jsonb)",(json.dumps(item),))
