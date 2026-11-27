import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_extended_topics import stage,load
from pipelines.import_genesis_places import uid
R=uid("test-release:extended-topics")
PRIOR=uid("test-release:cells")
class TopicIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=stage(conn)
            assert len(cls.ids)==7 and cls.ids==stage(conn)
            assert conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]==PRIOR
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(PRIOR,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+cls.ids))
        cls.client=TestClient(app)
    def get(self,params=None):
        r=self.client.get("/api/v1/extended-topics",params=params)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()
    def test_exact_content(self):
        original={x["id"]:x for _,_,_,items in load() for x in items}
        rows=self.get()["topics"]
        self.assertEqual({x["id"]:{k:x[k] for k in ("id","type","record")} for x in rows},original)
        self.assertEqual(len(rows),7)
    def test_anchors(self):
        rows=self.get()["topics"]
        self.assertEqual(next(x["location"] for x in rows if x["id"]=="FAYD_425E270N_S"),[42.50815,27.06977])
        self.assertEqual(next(x["location"] for x in rows if x["id"]=="north-riyadh"),[45.8618,25.2971])
        self.assertTrue(all(x["directory_entity_id"] for x in rows if x["type"]=="story"))
    def test_release_scope(self):
        self.assertEqual(self.get({"release":str(PRIOR)})["topics"],[])
        self.assertEqual(len(self.client.get("/api/v1/articles").json()["articles"]),50)
    def test_internal_tasks(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],7)
    def test_invalid_source(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("""SELECT knowledge.validate_topic('{"id":"a","type":"story","record":{"title":"a","lead":"b","sections":[["a","b"]],"sources":[["a","javascript:bad"]]}}'::jsonb)""")
