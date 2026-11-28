import unittest
from dataclasses import replace
from contracts.publication import Claim, Reference, PolicyStore


class PublicationPolicyTests(unittest.TestCase):
    def setUp(self):
        # All invented IDs, no historical facts. Test store never persists or serves them.
        self.store = PolicyStore({"p": "Person", "a": "Place", "b": "Place", "w": "Work"}, {"s": "Example source"})
        self.c = Claim("c", "v1", "p", "BORN_IN", "a")

    def publish(self, *members, release="r1"):
        return self.store.publish(release, members, role="publication_service")

    def test_unsourced_unreviewed_publishes(self):
        self.store.stage(self.c)
        self.publish("v1")
        self.assertEqual(self.store.read()["claims"][0]["object_id"], "a")
        self.assertEqual(self.store.tasks(role="curator"), {"v1": ("documentation", "review")})

    def test_unsupported_not_automatically_incorrect(self):
        self.store.stage(replace(self.c, epistemic_status="unsupported"))
        self.publish("v1")
        self.assertEqual(len(self.store.read()["claims"]), 1)

    def test_optional_reference_and_missing_locator(self):
        self.store.stage(replace(self.c, references=(Reference("s"),)))
        self.publish("v1")
        self.assertEqual(self.store.read()["claims"][0]["references"], [{"source_version_id": "s", "title": "Example source"}])
        self.assertIn("documentation", self.store.tasks(role="curator")["v1"])

    def test_available_reference_and_scientific_note(self):
        self.store.stage(replace(self.c, references=(Reference("s", "p. 1"),), verification_status="verified", scientific_note="Approximate location"))
        self.publish("v1")
        row = self.store.read()["claims"][0]
        self.assertEqual(row["scientific_note"], "Approximate location")
        self.assertEqual(row["references"][0]["locator"], "p. 1")
        self.assertEqual(self.store.tasks(role="curator"), {})

    def test_internal_fields_not_public(self):
        self.store.stage(replace(self.c, correction_status="pending"))
        self.publish("v1")
        self.assertEqual(set(self.store.read()["claims"][0]), {"claim_id", "version_id", "subject_id", "predicate", "object_id"})
        with self.assertRaises(PermissionError):
            self.store.tasks(role="public")
        with self.assertRaises(PermissionError):
            self.store.correction_log(role="public")

    def test_forbidden_members(self):
        for i, kwargs in enumerate(({"synthetic": True}, {"restricted": True}, {"verification_status": "known_incorrect"})):
            v = str(i)
            self.store.stage(replace(self.c, claim_id=v, version_id=v, **kwargs))
            with self.assertRaises(ValueError):
                self.publish(v)

    def test_stage_not_public_and_agent_cannot_publish(self):
        self.store.stage(self.c)
        with self.assertRaises(PermissionError):
            self.store.publish("r1", ["v1"], role="agent")
        self.publish()
        self.assertEqual(self.store.read()["claims"], [])

    def test_invalid_reference_or_relation(self):
        for bad in (replace(self.c, object_id="w"), replace(self.c, object_id="missing"), replace(self.c, references=(Reference("absent"),)), replace(self.c, predicate="INFLUENCED")):
            with self.assertRaises(ValueError):
                self.store.stage(bad)

    def test_known_correction_new_release_old_manifest_retained(self):
        self.store.stage(self.c)
        old = self.publish("v1")
        new = replace(self.c, version_id="v2", object_id="b")
        release = self.store.correct("v1", new, reason="Known wrong value", basis="Test rule", actor="test", role="publication_service", release_id="r2")
        self.assertEqual(self.store.read()["claims"][0]["object_id"], "b")
        self.assertEqual(self.store.read("r1")["claims"], [])
        self.assertEqual(self.store.manifest("r1", role="curator"), old)
        self.assertNotEqual(old.manifest_sha256, release.manifest_sha256)
        log = self.store.correction_log(role="curator")[0]
        self.assertEqual((log.previous.object_id, log.replacement.object_id, log.basis), ("a", "b", "Test rule"))
        self.assertEqual(log.replacement.correction_status, "corrected")
        self.assertEqual(self.store.tasks(role="curator"), {"v2": ("documentation", "review")})

    def test_unknown_correction_suppresses_only_wrong_claim(self):
        self.store.stage(self.c)
        self.store.stage(replace(self.c, claim_id="other", version_id="other", object_id="b"))
        self.publish("v1", "other")
        self.store.flag_incorrect("v1", role="curator")
        self.assertEqual([c["claim_id"] for c in self.store.read()["claims"]], ["other"])
        self.assertIn("correction", self.store.tasks(role="curator")["v1"])
        self.assertEqual(self.store.correction_log(role="curator"), ())

    def test_invalid_correction_has_no_side_effect(self):
        self.store.stage(self.c)
        self.publish("v1")
        new = replace(self.c, version_id="v2", object_id="b")
        for basis, release_id in (("", "r2"), ("known", "r1")):
            with self.assertRaises(ValueError):
                self.store.correct("v1", new, reason="test", basis=basis, actor="test", role="publication_service", release_id=release_id)
        self.assertEqual(self.store.read()["claims"][0]["object_id"], "a")
        self.assertEqual(self.store.correction_log(role="curator"), ())

    def test_deterministic_manifest_and_no_duplicate_versions(self):
        self.store.stage(self.c)
        self.store.stage(replace(self.c, claim_id="other", version_id="other", object_id="b"))
        first = self.publish("v1", "other")
        second = self.publish("other", "v1", release="r2")
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        with self.assertRaises(ValueError):
            self.publish("v1", "v1", release="r3")


if __name__ == "__main__":
    unittest.main()
