"""Run last on disposable CI database: actual reader HTTP after committed revocation."""
import os
import unittest
from uuid import uuid4
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app

class AccessRevocationIntegration(unittest.TestCase):
    def test_public_endpoints_after_revocation(self):
        p,c,v,s1,s2,r1,r2,r3=[uuid4() for _ in range(8)]
        g1,g2=sorted([uuid4(),uuid4()])
        client=TestClient(app)
        def get(path,**params):
            response=client.get(path,params=params)
            self.assertEqual(response.status_code,200,response.text)
            return response.json()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            try:
                conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Place')",(p,))
                conn.execute("INSERT INTO knowledge.claim VALUES(%s)",(c,))
                conn.execute("INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language) VALUES(%s,%s,%s,'NAME','Revocation fixture','en')",(v,c,p))
                for source,title in [(s1,"Hidden fixture source"),(s2,"Retained fixture source")]:
                    conn.execute("INSERT INTO knowledge.source_version(id,title) VALUES(%s,%s)",(source,title))
                    conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator) VALUES(%s,%s,%s,'fixture')",(uuid4(),v,source))
                for gid,x,y in [(g1,39,21),(g2,44,24)]:
                    conn.execute("INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation) VALUES(%s,%s,'location',public.ST_SetSRID(public.ST_Point(%s,%s),4326),'exact','fixture')",(gid,v,x,y))
                h1=conn.execute("SELECT knowledge.publish(%s,%s)",(r1,[v])).fetchone()[0]
                conn.execute("SELECT knowledge.publish(%s,%s)",(r2,[v]))
                conn.commit()
                path="/api/v1/claims/"+str(c)
                self.assertEqual(len(get(path,release=str(r1))["claim"]["references"]),2)
                self.assertEqual(len(get("/api/v1/map/features",release=str(r1),bbox="38,20,40,22")["features"]),1)
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.revoke_source(%s,'private reason','fixture curator')",(s1,))
                conn.execute("SELECT knowledge.revoke_geometry(%s,%s,1,'private reason','fixture curator')",(r1,v))
                conn.commit()
                for release in (r1,r2):
                    row=get(path,release=str(release))["claim"]
                    self.assertEqual([x["title"] for x in row["references"]],["Retained fixture source"])
                    self.assertEqual([x["geometry"]["coordinates"] for x in row["geometries"]],[[44,24]])
                    self.assertNotIn("private reason",str(row))
                    self.assertEqual(get("/api/v1/map/features",release=str(release),bbox="38,20,40,22")["features"],[])
                    self.assertEqual(len(get("/api/v1/map/features",release=str(release),bbox="43,23,45,25")["features"]),1)
                    self.assertEqual(len(get("/api/v1/explore",release=str(release),q="Revocation fixture")["results"]),1)
                    self.assertEqual(get("/api/v1/relations",release=str(release),entity_id=str(p))["claims"],[])
                self.assertEqual(conn.execute("SELECT knowledge.publish(%s,%s)",(r3,[v])).fetchone()[0],h1)
                self.assertTrue(conn.execute("SELECT knowledge.verify_release(%s)",(r1,)).fetchone()[0])
                conn.commit()
                self.assertEqual(get("/api/v1/map/features",release=str(r3),bbox="38,20,40,22")["features"],[])
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.withhold_version(%s,'access policy','fixture curator')",(v,))
                conn.commit()
                self.assertEqual(client.get(path,params={"release":str(r1)}).status_code,404)
                self.assertEqual(get("/api/v1/explore",release=str(r1),q="Revocation fixture")["results"],[])
                self.assertTrue(conn.execute("SELECT knowledge.verify_release(%s)",(r1,)).fetchone()[0])
            finally:
                conn.rollback()
                # Test-only pointer restoration; never run this fixture on production.
                conn.execute("UPDATE knowledge.current_release SET release_id=%s",(prior,))
                conn.commit()
