import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_genesis_places import uid
from pipelines.import_encyclopedia import load,stage

R=uid("test-release:encyclopedia")
PRIOR=uid("test-release:genesis-sample")

class ArticlesIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.source=load()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=stage(conn)
            assert cls.ids==stage(conn)
            assert conn.execute("SELECT count(*) FROM knowledge.legacy_crosswalk WHERE namespace='encyclopedia-v0.13'").fetchone()[0]==50
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(PRIOR,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+cls.ids))
        cls.client=TestClient(app)

    def get(self,path,params=None,status=200):
        r=self.client.get(path,params=params)
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def test_complete_exact_content(self):
        result=self.get("/api/v1/articles",{"release":str(R)})
        self.assertEqual(len(result["articles"]),50)
        for original in self.source["articles"]:
            response=self.get("/api/v1/articles/"+original["id"],{"release":str(R)})
            row=response["article"]
            titles={a["id"]:a["title"] for a in self.source["articles"]}
            self.assertEqual(response["related_topics"],[{"id":s,"title":titles[s]} for s in original["related"]])
            self.assertEqual({k:row[k] for k in original},original)
            self.assertEqual(row["bibliography"],[{"id":s,"title":self.source["sources"][s][0],"url":self.source["sources"][s][1]} for s in original["sources"]])
            self.assertEqual(set(row),set(original)|{"bibliography"})

    def test_era_and_search(self):
        r=self.get("/api/v1/articles",{"era":"ancient","q":"الحجر","release":str(R)})
        self.assertIn("hegra",[a["id"] for a in r["articles"]])
        self.assertTrue(all("ancient" in a["eras"] for a in r["articles"]))
        self.assertEqual(self.get("/api/v1/articles",{"q":"%","release":str(R)})["articles"],[])
        self.get("/api/v1/articles",{"q":"ـ"},422)

    def test_release_and_relation_isolation(self):
        self.assertEqual(self.get("/api/v1/articles",{"release":str(PRIOR)})["articles"],[])
        self.get("/api/v1/articles/hegra",{"release":str(PRIOR)},404)
        row=self.get("/api/v1/articles/hegra")
        self.assertEqual(row["release_id"],str(R))
        self.assertEqual(self.get("/api/v1/relations",{"entity_id":row["work_id"]})["claims"],[])
        self.assertEqual(len(self.get("/api/v1/map/features",{"bbox":"-180,-85,180,85"})["features"]),3)

    def test_internal_tasks_and_source_identity(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],50)
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.evidence WHERE version_id=ANY(%s)",(self.ids,)).fetchone()[0],50)
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("SELECT knowledge.validate_article('{\"internal_status\":\"draft\"}'::jsonb)")
