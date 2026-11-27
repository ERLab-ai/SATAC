import copy
import unittest
from pipelines.compare_performance import compare

class PerformanceComparisonTests(unittest.TestCase):
    def fixture(self):
        return {"mode":"reference","release_id":"fixture","claim_versions":1,"server_commit":"base","measurements":[
            {"case":"map","path":"/map","parameters":{"release":"fixture"},"requests":100,"warmup":10,
             "result_count":1,"response_sha256":"same","has_next_page":False,"p95_ms":100.0}]}
    def test_same_response(self):
        b=self.fixture();a=copy.deepcopy(b);a["server_commit"]="new";a["measurements"][0]["p95_ms"]=25.0
        r=compare(b,a)
        self.assertTrue(r["identical_public_responses"])
        self.assertEqual(r["comparison"][0]["p95_reduction_pct"],75.0)
    def test_different_payload_rejected(self):
        b=self.fixture();a=copy.deepcopy(b);a["measurements"][0]["response_sha256"]="different"
        with self.assertRaisesRegex(ValueError,"response_sha256"):
            compare(b,a)
    def test_different_release_rejected(self):
        b=self.fixture();a=copy.deepcopy(b);a["release_id"]="other"
        with self.assertRaisesRegex(ValueError,"release_id"):
            compare(b,a)
