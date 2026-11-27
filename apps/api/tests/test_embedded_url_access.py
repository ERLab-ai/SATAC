"""Isolated CI fixture: exact embedded URL withholding across immutable releases."""
import os
import unittest
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
from apps.api.main import app


class EmbeddedURLAccess(unittest.TestCase):
    def test_exact_nested_url_across_releases(self):
        client=TestClient(app)
        r1,r2,r3=[uuid4() for _ in range(3)]
        url="https://example.invalid/satac-a07"
        versions=[]
        claims=[]
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            try:
                for i,link in enumerate([url,url+"/retained"]):
                    entity,claim,version=[uuid4() for _ in range(3)]
                    claims.append(claim)
                    versions.append(version)
                    slug="url_fixture_"+str(i)
                    article={"id":slug,"title":"URL fixture "+str(i),"subtitle":"Disposable CI only",
                             "category":"fixture","art":"globe","summary":"Fixture summary",
                             "keywords":"urlfixture","eras":[],"location":[0,0],
                             "sections":[{"title":"Fixture","text":"Invented test text"}],
                             "sources":["test"],"related":[],
                             "bibliography":[{"id":"test","title":"Fixture bibliography","url":link}]}
                    conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Work')",(entity,))
                    conn.execute("INSERT INTO knowledge.claim VALUES(%s)",(claim,))
                    conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language)
                                 VALUES(%s,%s,%s,'ARTICLE',%s::jsonb::text,'ar')""",(version,claim,entity,Jsonb(article)))
                h1=conn.execute("SELECT knowledge.publish(%s,%s)",(r1,versions)).fetchone()[0]
                h2=conn.execute("SELECT knowledge.publish(%s,%s)",(r2,versions)).fetchone()[0]
                conn.commit()
                self.assertEqual(h1,h2)
                def get(path,release=r1,status=200,**params):
                    resp=client.get(path,params={"release":str(release),**params})
                    self.assertEqual(resp.status_code,status,resp.text)
                    return resp.json()
                self.assertEqual(len(get("/api/v1/articles")["articles"]),2)
                self.assertEqual(get("/api/v1/articles/url_fixture_0")["article"]["bibliography"][0]["url"],url)
                self.assertEqual(len(get("/api/v1/explore",q="urlfixture")["references"]),2)
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.revoke_embedded_url(%s,'private fixture reason','fixture curator')",(url,))
                conn.commit()
                for rid in (r1,r2):
                    self.assertEqual([a["id"] for a in get("/api/v1/articles",rid)["articles"]],["url_fixture_1"])
                    get("/api/v1/articles/url_fixture_0",rid,404)
                    get("/api/v1/claims/"+str(claims[0]),rid,404)
                    self.assertEqual(get("/api/v1/articles/url_fixture_1",rid)["article"]["bibliography"][0]["url"],url+"/retained")
                    hits=get("/api/v1/explore",rid,q="urlfixture")["references"]
                    self.assertEqual([h["id"] for h in hits],["url_fixture_1"])
                    self.assertTrue(conn.execute("SELECT knowledge.verify_release(%s)",(rid,)).fetchone()[0])
                self.assertEqual(conn.execute("SELECT knowledge.publish(%s,%s)",(r3,versions)).fetchone()[0],h1)
                conn.commit()
                self.assertEqual([a["id"] for a in get("/api/v1/articles",r3)["articles"]],["url_fixture_1"])
                conn.execute("SELECT knowledge.activate_release(%s,%s,%s,'fixture rollback','fixture publisher')",(r3,r1,h1))
                conn.commit()
                self.assertEqual([a["id"] for a in client.get("/api/v1/articles").json()["articles"]],["url_fixture_1"])
                self.assertFalse(conn.execute("SELECT has_table_privilege('satac_reader','knowledge.embedded_url_revocation','SELECT')").fetchone()[0])
            finally:
                conn.rollback()
                # Disposable test DB only; restore the prior candidate pointer.
                conn.execute("UPDATE knowledge.current_release SET release_id=%s",(prior,))
                conn.commit()
