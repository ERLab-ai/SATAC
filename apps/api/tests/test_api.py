import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from apps.api.main import app

P="00000000-0000-0000-0000-000000000001"
C1="10000000-0000-0000-0000-000000000001"
C2="10000000-0000-0000-0000-000000000002"
C3="10000000-0000-0000-0000-000000000003"
R1="40000000-0000-0000-0000-000000000001"
R2="40000000-0000-0000-0000-000000000002"


class ApiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)

    def get(self,path,params=None,status=200):
        r=self.client.get(path,params=params)
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def test_health_and_openapi(self):
        self.assertEqual(self.get("/health"),{"status":"ok"})
        paths=self.get("/openapi.json")["paths"]
        self.assertIn("/api/v1/map/features",paths)
        self.assertFalse(any(p.startswith("/internal") for p in paths))

    def test_releases(self):
        r=self.get("/api/v1/releases",{"limit":1})
        self.assertEqual(r["releases"][0]["release_id"],R1)
        self.assertEqual(r["next_after"],R1)
        second=self.get("/api/v1/releases",{"after":R1})
        self.assertTrue(second["releases"][0]["is_current"])

    def test_unsourced_claim_no_admin_fields(self):
        r=self.get("/api/v1/claims/"+C1)
        self.assertEqual(r["release_id"],R2)
        row=r["claim"]
        self.assertEqual(set(row),{"claim_id","version_id","subject_id","predicate","object_id","scientific_note","temporal","geometries"})
        self.assertEqual(len(row["geometries"]),1)
        self.assertEqual(row["scientific_note"],"Approximate fixture")

    def test_available_reference_and_restricted_source(self):
        row=self.get("/api/v1/claims/"+C2)["claim"]
        self.assertEqual(len(row["references"]),1)
        self.assertEqual(row["references"][0]["title"],"Example source")
        self.assertEqual(row["references"][0]["locator"],"p. 1")
        self.assertEqual(row["references"][0]["stance"],"context")

    def test_withdrawal_in_historical_release(self):
        self.get("/api/v1/claims/"+C3,{"release":R1},404)
        self.get("/api/v1/claims/"+C1,{"release":"40000000-0000-0000-0000-000000000099"},404)

    def test_deep_time_exact_strings(self):
        row=self.get("/api/v1/claims/"+C2)["claim"]
        self.assertEqual(row["temporal"]["start_low"],"-999999999999999999999999999999")
        r=self.get("/api/v1/relations",{"entity_id":P,"as_of":row["temporal"]["start_low"]})
        self.assertEqual([x["claim_id"] for x in r["claims"]],[C2])

    def test_time_filters(self):
        def ids(**kw):
            return [r["claim_id"] for r in self.get("/api/v1/relations",{"entity_id":P,**kw})["claims"]]
        self.assertEqual(ids(as_of="450",certainty="possible"),[C1])
        self.assertEqual(ids(as_of="450",certainty="certain"),[])
        self.assertEqual(ids(as_of="550",certainty="certain"),[C1])
        self.assertEqual(ids(**{"from":"600","to":"650"}),[C1])

    def test_keyset_and_direction(self):
        r=self.get("/api/v1/relations",{"entity_id":P,"direction":"out","limit":1,"max_depth":1})
        self.assertEqual([x["claim_id"] for x in r["claims"]],[C1])
        r2=self.get("/api/v1/relations",{"entity_id":P,"release":r["release_id"],"after":r["next_after"],"limit":1})
        self.assertEqual([x["claim_id"] for x in r2["claims"]],[C2])
        self.assertIsNone(r2["next_after"])
        self.assertEqual(self.get("/api/v1/relations",{"entity_id":P,"direction":"in"})["claims"],[])
        self.get("/api/v1/relations",{"entity_id":P,"after":r["next_after"]},422)
        self.get("/api/v1/relations",{"entity_id":P,"max_depth":2},422)

    def test_map_bbox_lens_and_withdrawal(self):
        r=self.get("/api/v1/map/features",{"bbox":"38,20,41,23","lens":"location","release":R1,"as_of":"550"})
        self.assertEqual(r["type"],"FeatureCollection")
        self.assertEqual(len(r["features"]),1)
        self.assertEqual(r["features"][0]["geometry"]["coordinates"],[39,21])
        self.assertEqual(self.get("/api/v1/map/features",{"bbox":"38,20,41,23","lens":"trade"})["features"],[])

    def test_cross_antimeridian(self):
        r=self.get("/api/v1/map/features",{"bbox":"170,-10,-170,10"})
        self.assertEqual(sorted(f["geometry"]["coordinates"][0] for f in r["features"]),[-179,179])

    def test_bad_query(self):
        for q in ({"bbox":"0,0,1,100"},{"bbox":"nan,0,1,2"},{"bbox":"0,0,1,2","as_of":"0","from":"1","to":"2"},{"bbox":"0,0,1,2","from":"1"},{"bbox":"0,0,1,2","as_of":"1.5"},{"bbox":"0,0,1,2","certainty":"certain"}):
            self.get("/api/v1/map/features",q,422)

    def test_reject_elevated_login(self):
        with patch.dict(os.environ,{"SATAC_READER_DSN":os.environ["SATAC_ADMIN_TEST_DSN"]}):
            self.assertEqual(self.get("/health",status=503)["error"]["code"],"reader_configuration_invalid")


if __name__=="__main__":
    unittest.main()
