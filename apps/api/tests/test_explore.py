import unittest
from fastapi.testclient import TestClient
from apps.api.main import app
from pipelines.import_genesis_places import uid

class ExploreIntegration(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
    def search(self,q,**params):
        r=self.client.get("/api/v1/explore",params={"q":q,**params})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()
    def test_cross_collection(self):
        r=self.search("فيد")
        self.assertTrue({"historical","topic"}<={x["kind"] for x in r["references"]})
        self.assertEqual(r["reference_semantics"],"context_not_temporal_matches")
        self.assertTrue(any(x["kind"]=="geology" for x in self.search("Hutaymah")["references"]))
        self.assertTrue(any(x["kind"]=="modern" for x in self.search("Riyadh")["references"]))
    def test_temporal_isolation(self):
        r=self.search("الحجر",as_of="550")
        self.assertEqual(r["results"],[])
        self.assertTrue(any(x["kind"]=="article" for x in r["references"]))
        self.assertTrue(any(x["kind"]=="snapshot" for x in self.search("1727",as_of="550")["references"]))
    def test_release_isolation(self):
        r=self.search("سلمى",release=str(uid("test-release:cells")))
        self.assertFalse(any(x["kind"]=="topic" for x in r["references"]))
        self.assertTrue(any(x["kind"]=="topic" for x in self.search("سلمى")["references"]))
    def test_validation(self):
        self.assertEqual(self.search("%")["references"],[])
        self.assertEqual(self.client.get("/api/v1/explore",params={"q":"ـ"}).status_code,422)
        self.assertEqual(self.client.get("/api/v1/explore",params={"q":"فيد","as_of":"bad"}).status_code,422)
        self.assertEqual(self.client.get("/api/v1/explore",params={"q":"فيد","after":str(uid("unknown"))}).status_code,422)
