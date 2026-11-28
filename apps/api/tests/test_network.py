import os
import unittest
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_genesis_places import uid
from pipelines.import_encyclopedia import load
from pipelines.import_editorial_network import stage

R=uid("test-release:editorial-network")
PRIOR=uid("test-release:encyclopedia")

class NetworkIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.source=load()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            cls.ids=stage(conn)
            assert cls.ids==stage(conn) and len(cls.ids)==21
            members=[r[0] for r in conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(PRIOR,))]
            conn.execute("SELECT knowledge.publish(%s,%s)",(R,members+cls.ids))
        cls.client=TestClient(app)

    def get(self,params=None):
        r=self.client.get("/api/v1/editorial-network",params=params)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def test_original_order_and_content(self):
        r=self.get({"release":str(R)})
        self.assertEqual([x["record"] for x in r["links"]],self.source["links"])
        self.assertEqual([x["record"] for x in r["journeys"]],self.source["journeys"])
        self.assertEqual(r["geometry_semantics"],"editorial_connections_not_routes")
        self.assertEqual(len(r["articles"]),50)

    def test_prior_release(self):
        r=self.get({"release":str(PRIOR)})
        self.assertEqual(r["links"],[])
        self.assertEqual(r["journeys"],[])

    def test_internal_tasks(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM knowledge.review_task WHERE version_id=ANY(%s) AND reason='review' AND resolved_at IS NULL",(self.ids,)).fetchone()[0],21)

    def test_missing_endpoint_excludes_whole_record(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            temporary=uid("test-release:network-partial")
            rows=conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s AND coalesce(payload->'article'->>'id','')<>'hegra'",(R,)).fetchall()
            conn.execute("SELECT knowledge.publish(%s,%s)",(temporary,[x[0] for x in rows]))
        try:
            result=self.get({"release":str(temporary)})
            self.assertFalse(any("hegra" in x["record"][:2] for x in result["links"]))
            self.assertFalse(any("hegra" in x["record"]["ids"] for x in result["journeys"]))
        finally:
            with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
                # Restore active pointer through normal publication, not mutation of snapshots.
                rows=conn.execute("SELECT version_id FROM knowledge.release_member WHERE release_id=%s",(R,)).fetchall()
                conn.execute("SELECT knowledge.publish(%s,%s)",(uid("test-release:network-restored"),[x[0] for x in rows]))

    def test_invalid_record(self):
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute("SELECT knowledge.validate_editorial('EDITORIAL_LINK','{\"ordinal\":0,\"record\":[\"a\",\"a\",\"label\"]}'::jsonb)")
