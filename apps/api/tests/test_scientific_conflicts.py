"""A05 real reader/API test and isolated browser release; disposable CI database only."""
import os
import unittest
from uuid import UUID, uuid4
import psycopg
from fastapi.testclient import TestClient
from apps.api.main import app

BROWSER_RELEASE = UUID("a0500000-0000-4000-8000-000000000001")
BROWSER_SUBJECT = UUID("a0500000-0000-4000-8000-000000000002")


class ScientificConflictIntegration(unittest.TestCase):
    def test_scientific_conflicts(self):
        subject=BROWSER_SUBJECT
        places=[uuid4() for _ in range(3)]
        group,source_a,source_b,source_hidden,other_release=[uuid4() for _ in range(5)]
        alt_claims=[uuid4() for _ in range(3)]
        alt_versions=sorted([uuid4() for _ in range(3)])
        name_versions=[uuid4() for _ in range(4)]
        client=TestClient(app)
        def get(release=BROWSER_RELEASE, **params):
            resp=client.get("/api/v1/conflicts",params={"entity_id":str(subject),"release":str(release),**params})
            self.assertEqual(resp.status_code,200,resp.text)
            return resp.json()
        with psycopg.connect(os.environ["SATAC_ADMIN_TEST_DSN"]) as conn:
            prior=conn.execute("SELECT release_id FROM knowledge.current_release").fetchone()[0]
            try:
                conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Person')",(subject,))
                for p in places:
                    conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Place')",(p,))
                conn.execute("INSERT INTO knowledge.scientific_conflict_group VALUES(%s,%s,'BORN_IN')",(group,subject))
                for entity,name,version in zip([subject,*places],["شخصية اختبار التعارض","الموضع التجريبي الأول","الموضع التجريبي الثاني","الموضع المحجوب"],name_versions):
                    c=uuid4()
                    conn.execute("INSERT INTO knowledge.claim VALUES(%s)",(c,))
                    conn.execute("INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language) VALUES(%s,%s,%s,'NAME',%s,'ar')",(version,c,entity,name))
                for c,v,p,note in zip(alt_claims,alt_versions,places,["رواية اختبار أولى","رواية اختبار ثانية","رواية محجوبة"]):
                    conn.execute("INSERT INTO knowledge.claim VALUES(%s)",(c,))
                    conn.execute("INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,scientific_note,conflict_group_id) VALUES(%s,%s,%s,'BORN_IN',%s,%s,%s)",(v,c,subject,p,note,group))
                for s,title,v,loc in [(source_a,"مصدر اختبار أول",alt_versions[0],"p. 11"),(source_b,"مصدر اختبار ثان",alt_versions[1],"p. 22"),(source_hidden,"مصدر محجوب",alt_versions[1],"private locator")]:
                    conn.execute("INSERT INTO knowledge.source_version(id,title) VALUES(%s,%s)",(s,title))
                    conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'supports')",(uuid4(),v,s,loc))
                conn.execute("INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation) VALUES(%s,%s,'location',public.ST_SetSRID(public.ST_Point(42,22),4326),'approximate','fixture')",(uuid4(),alt_versions[1]))
                conn.execute("SELECT knowledge.publish(%s,%s)",(BROWSER_RELEASE,name_versions+alt_versions))
                conn.execute("SELECT knowledge.publish(%s,%s)",(other_release,name_versions+[alt_versions[0],alt_versions[2]]))
                # Restore actual candidate current pointer immediately; browser fixture is archive only.
                conn.execute("UPDATE knowledge.current_release SET release_id=%s",(prior,))
                conn.commit()
                row=get()["conflicts"][0]
                self.assertEqual(row["alternative_count"],3)
                self.assertEqual([a["object_name"] for a in row["alternatives"]],["الموضع التجريبي الأول","الموضع التجريبي الثاني","الموضع المحجوب"])
                self.assertEqual(row["alternatives"][0]["references"][0]["locator"],"p. 11")
                self.assertEqual(row["alternatives"][1]["geometries"][0]["precision"],"approximate")
                self.assertEqual(get(prior)["conflicts"],[])
                self.assertEqual(len(get(other_release)["conflicts"][0]["alternatives"]),2)
                self.assertEqual(len(get(group_id=str(group),alternative_after=str(alt_versions[0]))["conflicts"][0]["alternatives"]),2)
                self.assertEqual(client.get("/api/v1/conflicts",params={"entity_id":str(subject),"after":str(group)}).status_code,422)
                self.assertEqual(client.get("/api/v1/conflicts",params={"entity_id":str(subject),"release":str(BROWSER_RELEASE),"group_id":str(uuid4())}).status_code,404)
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.revoke_source(%s,'private revocation','fixture')",(source_hidden,))
                conn.execute("SELECT knowledge.revoke_geometry(%s,%s,1,'private geometry','fixture')",(BROWSER_RELEASE,alt_versions[1]))
                conn.execute("SELECT knowledge.withhold_version(%s,'private withholding','fixture')",(alt_versions[2],))
                conn.commit()
                row=get()["conflicts"][0]
                self.assertEqual(row["alternative_count"],2)
                self.assertEqual([a["references"][0]["title"] for a in row["alternatives"]],["مصدر اختبار أول","مصدر اختبار ثان"])
                self.assertEqual(len(row["alternatives"][1]["references"]),1)
                self.assertNotIn("geometries",row["alternatives"][1])
                for key in ("verification_status","review_task","private locator","private withholding","رواية محجوبة","مصدر محجوب"):
                    self.assertNotIn(key,str(row))
                self.assertEqual(get(other_release)["conflicts"],[])
                self.assertTrue(conn.execute("SELECT knowledge.verify_release(%s)",(BROWSER_RELEASE,)).fetchone()[0])
            finally:
                conn.rollback()
                conn.execute("UPDATE knowledge.current_release SET release_id=%s",(prior,))
                conn.commit()
