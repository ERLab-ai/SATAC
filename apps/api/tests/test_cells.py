import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_cells import load,stage
from pipelines.import_genesis_places import uid

R=uid("test-release:cells")
PRIOR=uid("test-release:geology")
class CellsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.original,_,cls.geo=load()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=stage(conn)
            assert len(cls.ids)==2480 and cls.ids==stage(conn)
            assert conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]==PRIOR
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(PRIOR,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+cls.ids))
        cls.client=TestClient(app)
    def get(self,params=None):
        r=self.client.get("/api/v1/cells",params=params)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()
    def test_all_original_metrics(self):
        rows=self.get()["cells"]
        self.assertEqual(len(rows),2480)
        self.assertEqual({x["id"]:[x["c"],x["t"],x["area_km2"],x["water_km"]] for x in rows},{f"{r[0]},{r[1]}":r for r in self.original["rows"]})
        self.assertEqual(sum(x["water_km"]>0 for x in rows),251)
        self.assertAlmostEqual(sum(x["water_km"] for x in rows),11807.8,places=1)
    def test_original_associations(self):
        rows=self.get()["cells"]
        self.assertEqual({x["id"]:x["province_ids"] for x in rows if x["province_ids"]},self.geo["cell_provinces"])
        self.assertEqual(len(self.get()["provinces"]),44)
    def test_release_scope(self):
        self.assertEqual(self.get({"release":str(PRIOR)})["cells"],[])
    def test_tasks(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],2480)
    def test_invalid(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("""SELECT knowledge.validate_cell('{"id":"551,131","c":551,"t":131,"area_km2":1848.9,"water_km":-1,"radius":0.72,"province_ids":[]}'::jsonb)""")
