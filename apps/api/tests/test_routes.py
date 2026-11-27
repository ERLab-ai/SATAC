import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_routes import load,stage
from pipelines.import_genesis_places import uid
from contracts.route_graph import shortest

R=uid("test-release:routes")
PRIOR=uid("test-release:directory")
A="MAKKA_398E213N_S_JAZI"
B="MADINA_396E244N_S_JAZI"

class RoutesIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.edges=load()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            ids=stage(conn)
            assert len(ids)==145 and ids==stage(conn)
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            assert prior==PRIOR
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(prior,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+ids))
            cls.ids=ids
        cls.client=TestClient(app)

    def get(self,path,params=None,status=200):
        r=self.client.get(path,params=params)
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def test_original_segments(self):
        r=self.get("/api/v1/routes",{"release":str(R)})
        self.assertEqual(r["segments"],sorted(self.edges,key=lambda e:e["id"]))
        self.assertEqual(len(r["nodes"]),135)
        self.assertEqual(next(x["name"] for x in r["nodes"] if x["id"]==A),"مكة")

    def test_path_and_reverse(self):
        r=self.get("/api/v1/routes/path",{"start":A,"end":B})
        reverse=self.get("/api/v1/routes/path",{"start":B,"end":A})
        by_id={e["id"]:e for e in self.edges}
        self.assertGreater(r["meters"],0)
        self.assertEqual(r["meters"],sum(by_id[s["id"]]["meters"] for s in r["steps"]))
        self.assertEqual(r["meters"],reverse["meters"])
        self.assertEqual(r["steps"][0]["from_id"],A)
        self.assertEqual(r["steps"][-1]["to_id"],B)
        for x,y in zip(r["steps"],r["steps"][1:]):
            self.assertEqual(x["to_id"],y["from_id"])
        self.assertEqual(self.get("/api/v1/routes/path",{"start":A,"end":A})["meters"],0)

    def test_scope_and_missing_node(self):
        self.assertEqual(self.get("/api/v1/routes",{"release":str(PRIOR)})["segments"],[])
        self.get("/api/v1/routes/path",{"start":A,"end":B,"release":str(PRIOR)},404)
        self.get("/api/v1/routes/path",{"start":"unknown","end":B},404)

    def test_shortest_weight_not_edge_count(self):
        e=[{"id":"a","from_id":"x","to_id":"y","meters":9},{"id":"b","from_id":"x","to_id":"z","meters":2},{"id":"c","from_id":"z","to_id":"y","meters":3},{"id":"d","from_id":"p","to_id":"q","meters":1}]
        self.assertEqual(shortest(e,"x","y")["meters"],5)
        self.assertIsNone(shortest(e,"x","p"))

    def test_internal_tasks(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],145)
