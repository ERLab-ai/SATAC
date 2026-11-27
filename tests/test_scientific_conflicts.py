"""A05 reference tests: invented data, no publication or database access."""
import unittest
from dataclasses import replace

from contracts.publication import Claim, PolicyStore, Reference


class ScientificConflictTests(unittest.TestCase):
    def setUp(self):
        self.store = PolicyStore(
            {"p": "Person", "q": "Person", "a": "Place", "b": "Place"},
            {"s1": "Fixture source A", "s2": "Fixture source B"},
        )
        self.first = Claim("c1", "v1", "p", "BORN_IN", "a",
                           references=(Reference("s1", "p. 1"),),
                           scientific_note="Fixture A", conflict_group_id="g")
        self.second = Claim("c2", "v2", "p", "BORN_IN", "b",
                            references=(Reference("s2", "p. 2"),),
                            scientific_note="Fixture B", conflict_group_id="g")
        self.store.stage(self.first)
        self.store.stage(self.second)

    def publish(self, rid, versions):
        return self.store.publish(rid, versions, role="publication_service")

    def test_two_alternatives_and_evidence_preserved(self):
        self.publish("r1", ["v2", "v1"])
        result = self.store.read_conflicts("r1")
        self.assertEqual(result["release_id"], "r1")
        alternatives = result["conflicts"][0]["alternatives"]
        self.assertEqual([a["claim_id"] for a in alternatives], ["c1", "c2"])
        self.assertEqual([a["object_id"] for a in alternatives], ["a", "b"])
        self.assertEqual([a["references"][0]["locator"] for a in alternatives], ["p. 1", "p. 2"])
        self.assertNotIn("verification_status", alternatives[0])
        self.assertNotIn("winner", result["conflicts"][0])

    def test_explicit_only_and_release_scoped(self):
        self.store.stage(replace(self.second, claim_id="c3", version_id="v3",
                                 conflict_group_id=None))
        self.publish("r1", ["v1", "v3"])
        self.assertEqual(self.store.read_conflicts("r1")["conflicts"], [])
        self.publish("r2", ["v1", "v2", "v3"])
        self.assertEqual(len(self.store.read_conflicts()["conflicts"]), 1)
        self.assertEqual(self.store.read_conflicts("r1")["conflicts"], [])

    def test_withdrawal_hides_conflict_without_rewriting_manifest(self):
        release = self.publish("r1", ["v1", "v2"])
        self.store.flag_incorrect("v2", role="curator")
        self.assertEqual(self.store.read_conflicts("r1")["conflicts"], [])
        self.assertEqual(self.store.manifest("r1", role="curator"), release)

    def test_missing_reference_does_not_block_publication(self):
        self.store.stage(replace(self.second, claim_id="c3", version_id="v3", references=()))
        self.publish("r1", ["v1", "v3"])
        alternatives = self.store.read_conflicts()["conflicts"][0]["alternatives"]
        self.assertNotIn("references", alternatives[1])
        self.assertIn("documentation", self.store.tasks(role="curator")["v3"])

    def test_mixed_subject_group_rejected_without_changing_current(self):
        self.publish("r1", ["v1", "v2"])
        self.store.stage(replace(self.second, claim_id="c3", version_id="v3", subject_id="q"))
        with self.assertRaises(ValueError):
            self.publish("r2", ["v1", "v3"])
        self.assertEqual(self.store.read_conflicts()["release_id"], "r1")

    def test_correction_mixed_group_rejected_atomically(self):
        self.publish("r1", ["v1", "v2"])
        replacement = replace(self.first, version_id="v4", subject_id="q")
        with self.assertRaises(ValueError):
            self.store.correct("v1", replacement, reason="fixture", basis="fixture",
                               actor="fixture", role="publication_service", release_id="r2")
        self.assertEqual(len(self.store.read_conflicts()["conflicts"][0]["alternatives"]), 2)
        self.assertEqual(self.store.correction_log(role="curator"), ())

    def test_synthetic_or_restricted_alternative_cannot_publish(self):
        for field in ("synthetic", "restricted"):
            v = "v-" + field
            self.store.stage(replace(self.second, claim_id=v, version_id=v, **{field: True}))
            with self.assertRaises(ValueError):
                self.publish("r-" + field, ["v1", v])


if __name__ == "__main__":
    unittest.main()
