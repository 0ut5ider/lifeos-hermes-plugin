# ABOUTME: Verifies native reviewers and direct writers share governed publication and revisions.
# ABOUTME: Uses real native curation, malformed input, and stale snapshots in synthetic stores.

import unittest

import test_memory_native as native_fixture


class MemoryCurationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.scope = native_fixture.OWNER

    def test_native_add_and_full_curation_preserve_current_references(self):
        saved = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal", "content": "RULE: original native fact"},
                                        request_id="native-first", project="general")
        self.assertTrue(saved["ok"], saved)
        first = self.memory.recall(self.scope, "original native fact")[0]
        observed = self.memory.read_hot(self.scope, "principal")
        curated = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal", "op": "set",
                                                      "entries": ["RULE: original native fact", "RULE: added native fact"]},
                                         request_id="native-set", project="general", observed_revision=observed["revision"])
        self.assertTrue(curated["ok"], curated)
        self.assertEqual(self.memory.get(self.scope, first["reference"])["status"], "ok")
        self.assertEqual(len(self.memory.recall(self.scope, "native fact")), 2)

    def test_stale_native_reviewer_cannot_overwrite_an_acknowledged_fact(self):
        self.fixture.remember("RULE: original native fact", "first", "principal")
        observed = self.memory.read_hot(self.scope, "principal")
        self.fixture.remember("RULE: acknowledged explicit fact", "second", "principal")
        result = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal", "op": "set",
                                                    "entries": ["RULE: reviewer replacement"]}, request_id="stale", project="general",
                                       observed_revision=observed["revision"])
        self.assertFalse(result["ok"])
        self.assertIn("revision", result["message"])
        self.assertEqual(len(self.memory.recall(self.scope, "fact")), 2)

    def test_forgotten_fact_cannot_return_with_changed_prefix_or_provenance(self):
        saved = self.fixture.remember("RULE: original retained fact", "first", "principal")
        self.memory.forget(self.scope, saved["reference"], "forget")
        result = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal",
                                                    "content": "PREFERENCE: Original retained fact ~inferred"}, request_id="resurrection", project="general")
        self.assertFalse(result["ok"])
        self.assertEqual(self.memory.recall(self.scope, "retained"), [])

    def test_direct_native_set_cannot_silently_drop_invalid_replacements(self):
        self.fixture.remember("RULE: original native fact", "first", "principal")
        observed = self.memory.read_hot(self.scope, "principal")
        result = self.memory.native_set(self.scope, "principal", ["RULE: " + "😀" * 129], "invalid", observed["revision"])
        self.assertFalse(result["ok"])
        self.assertEqual(len(self.memory.recall(self.scope, "original")), 1)


if __name__ == "__main__":
    unittest.main()
