"""Disposable CI only; actual public reader resolution and archive separation."""
import os
import unittest
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app


class CanonicalResolutionIntegration(unittest.TestCase):
    def test_release_scoped_identity_and_separation(self):
        a,b,s,r0,r1,r2=[uuid4() for _ in range(6)]
        client=TestClient(app)
        def get(path,r,status=200,**params):
            response=client.get(path,params={"release":str(r),**params})
            self.assertEqual(response.status_code,status,response.text)
            return response.json()
        path="/api/v1/entities/"+str(a)+"/canonical"
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            try:
                names=[]
                for entity,name in [(a,"Identity fixture alias"),(b,"Identity fixture canonical")]:
                    c,v=uuid4(),uuid4()
                    names.append(v)
                    conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Place')",(entity,))
                    conn.execute("INSERT INTO knowledge.claim VALUES(%s)",(c,))
                    conn.execute("INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language) VALUES(%s,%s,%s,'NAME',%s,'en')",(v,c,entity,name))
                conn.execute("INSERT INTO knowledge.source_version(id,title) VALUES(%s,'Identity fixture source')",(s,))
                conn.execute("SELECT knowledge.publish(%s,%s)",(r0,names))
                conn.execute("SET LOCAL ROLE satac_curator")
                p=conn.execute("SELECT knowledge.propose_identity(%s,%s,'fixture','fixture')",(a,b)).fetchone()[0]
                d=conn.execute("SELECT knowledge.decide_identity(%s,NULL,'same_entity','fixture','fixture',%s,'p. 1')",(p,s)).fetchone()[0]
                link=conn.execute("SELECT knowledge.stage_identity_link(%s,%s,%s)",(d,a,b)).fetchone()[0]
                conn.commit()
                self.assertIsNone(get(path,r0)["link"])
                h=conn.execute("SELECT knowledge.publish(%s,%s)",(r1,names+[link])).fetchone()[0]
                conn.commit()
                result=get(path,r1)
                self.assertEqual(result["canonical_id"],str(b))
                self.assertEqual(result["link"]["version_id"],str(link))
                self.assertEqual(result["link"]["references"][0]["locator"],"p. 1")
                self.assertNotIn("identity_decision_id",str(result))
                self.assertEqual(get("/api/v1/entities/"+str(b)+"/canonical",r1)["canonical_id"],str(b))
                self.assertEqual(get("/api/v1/entities/"+str(a),r1)["entity_id"],str(a))
                self.assertIsNone(get(path,r0)["link"])
                claim_id=result["link"]["claim_id"]
                self.assertIn(claim_id,[x["claim_id"] for x in get("/api/v1/export/claims",r1)["claims"]])
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.decide_identity(%s,%s,'distinct_entities','fixture split','fixture',NULL,NULL)",(p,d))
                conn.commit()
                self.assertIsNone(get(path,r1)["link"])
                get("/api/v1/claims/"+claim_id,r1,404)
                self.assertNotIn(claim_id,[x["claim_id"] for x in get("/api/v1/export/claims",r1)["claims"]])
                self.assertEqual(get("/api/v1/relations",r1,entity_id=str(a))["claims"],[])
                conn.execute("SELECT knowledge.publish(%s,%s)",(r2,names))
                conn.execute("SELECT knowledge.activate_release(%s,%s,%s,'fixture rollback','fixture')",(r2,r1,h))
                conn.commit()
                self.assertIsNone(get(path,r1)["link"])
                self.assertTrue(conn.execute("SELECT knowledge.verify_release(%s)",(r1,)).fetchone()[0])
            finally:
                conn.rollback()
                conn.execute("UPDATE knowledge.current_release SET release_id=%s",(prior,))
                conn.commit()
