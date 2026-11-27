"""Run after all benchmark/browser checks on the disposable CI database."""
import os
import unittest
from uuid import uuid4
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_genesis_places import uid

class EmbeddedSourceAccess(unittest.TestCase):
    def test_embedded_source_withholding(self):
        release=uid("test-release:encyclopedia")
        client=TestClient(app)
        def get(path,expected=200,**params):
            r=client.get(path,params={"release":str(release),**params})
            self.assertEqual(r.status_code,expected,r.text)
            return r.json()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            v,c,source=conn.execute("""SELECT version_id,(payload->>'claim_id')::uuid,
                (payload->'references'->0->>'source_version_id')::uuid
                FROM knowledge.release_member WHERE release_id=%s AND payload->'article'->>'id'='hegra'""",(release,)).fetchone()
            self.assertEqual(len(get("/api/v1/articles")["articles"]),50)
            self.assertEqual(get("/api/v1/articles/hegra")["article"]["id"],"hegra")
            self.assertTrue(get("/api/v1/explore",q="الحجر")["references"])
            original=conn.execute("SELECT manifest_sha256 FROM knowledge.release WHERE id=%s",(release,)).fetchone()[0]
            conn.execute("SET LOCAL ROLE satac_curator")
            conn.execute("SELECT knowledge.revoke_source(%s,'fixture evidence mask','fixture curator')",(source,))
            conn.commit()
            self.assertEqual(len(get("/api/v1/articles")["articles"]),50)
            self.assertNotIn("references",get("/api/v1/claims/"+str(c))["claim"])
            conn.execute("SET LOCAL ROLE satac_curator")
            conn.execute("SELECT knowledge.revoke_embedded_source(%s,'fixture embedded decision','fixture curator')",(source,))
            conn.commit()
            self.assertEqual(get("/api/v1/articles")["articles"],[])
            get("/api/v1/articles/hegra",404)
            get("/api/v1/claims/"+str(c),404)
            self.assertFalse(any(x["kind"]=="article" for x in get("/api/v1/explore",q="الحجر")["references"]))
            self.assertEqual(len(get("/api/v1/map/features",bbox="-180,-85,180,85")["features"]),3)
            self.assertEqual(conn.execute("SELECT manifest_sha256 FROM knowledge.release WHERE id=%s",(release,)).fetchone()[0],original)
            self.assertTrue(conn.execute("SELECT knowledge.verify_release(%s)",(release,)).fetchone()[0])
            self.assertFalse(conn.execute("SELECT has_table_privilege('satac_reader','knowledge.embedded_source_revocation','SELECT')").fetchone()[0])
