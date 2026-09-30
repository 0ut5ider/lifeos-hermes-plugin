# ABOUTME: Exercises governed memory operations against real native LifeOS tools.
# ABOUTME: Uses isolated synthetic user data for retries, curation, permissions, and concurrency.

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import MemoryScope


SOURCE = Path(os.environ.get("LIFEOS_MEMORY_SOURCE", str(Path.home() / ".cache/lifeos-plugin-memory/source/LifeOS/install")))
OWNER = MemoryScope("owner", "local:owner", ("assistant", "principal", "project"),
                    ("assistant", "principal", "project"), ("*",), "owner-test")
READER = MemoryScope("client", "mcp:reader", ("project",), (), ("lab",), "reader-test")


@unittest.skipUnless((SOURCE / "LIFEOS/TOOLS/MemorySystem.ts").is_file() and shutil.which("bun"),
                     "Native LifeOS source and Bun are required")
class NativeMemoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="native-memory-")
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.root = self.home / ".claude"
        (self.root / "LIFEOS").mkdir(parents=True)
        data = self.home / ".config/LIFEOS/USER"
        data.mkdir(parents=True)
        (data / "MEMORY").mkdir()
        (self.root / "LIFEOS/USER").symlink_to(data)
        (self.root / "LIFEOS/MEMORY").symlink_to(data / "MEMORY")
        (self.root / "LIFEOS/TOOLS").symlink_to(SOURCE / "LIFEOS/TOOLS")
        (self.root / "hooks").symlink_to(SOURCE / "hooks")
        for parent, filename in [("PRINCIPAL", "PRINCIPAL_MEMORY.md"),
                                 ("DIGITAL_ASSISTANT", "DA_MEMORY.md")]:
            target = data / parent / filename
            target.parent.mkdir()
            target.write_text("---\nlast_updated_by: synthetic\n---\n<!-- BEGIN ENTRIES -->\n<!-- END ENTRIES -->\n")
        (self.root / "settings.json").write_text("{}")
        self.memory = NativeMemory(self.root)

    def remember(self, content="The synthetic lab uses port 9123.", request="remember-one", category="project"):
        return self.memory.remember(OWNER, category=category, content=content,
                                    title="Synthetic lab routing", project="lab", request_id=request)

    def test_native_write_and_recall_share_the_authoritative_record(self):
        saved = self.remember()
        self.assertEqual(saved["status"], "committed")
        self.assertEqual(saved["writer"], OWNER.writer)
        self.assertEqual(saved["source"]["session"], "")
        results = self.memory.recall(READER, "synthetic lab")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["reference"], saved["reference"])
        self.assertIn("9123", results[0]["content"])
        self.assertTrue(list((self.root / "LIFEOS/MEMORY/KNOWLEDGE/Research").glob("*.md")))

    def test_retry_is_idempotent_and_changed_request_is_rejected(self):
        first = self.remember()
        again = self.remember()
        self.assertEqual(first, again)
        self.assertEqual(len(self.memory.recall(OWNER, "synthetic")), 1)
        conflict = self.remember(content="Changed payload with the same request identifier.")
        self.assertEqual(conflict["status"], "conflict")

    def test_correct_and_forget_exclude_retained_claims(self):
        first = self.remember()
        corrected = self.memory.correct(OWNER, first["reference"], "The synthetic lab uses port 9443.", "correct-one")
        self.assertEqual(corrected["status"], "committed")
        results = self.memory.recall(OWNER, "synthetic lab")
        self.assertEqual(len(results), 1)
        self.assertIn("9443", results[0]["content"])
        self.assertNotIn("9123", results[0]["content"])
        stale = self.memory.forget(OWNER, first["reference"], "forget-stale")
        self.assertEqual(stale["status"], "conflict")
        forgotten = self.memory.forget(OWNER, corrected["reference"], "forget-one")
        self.assertEqual(forgotten["status"], "committed")
        self.assertEqual(self.memory.recall(OWNER, "synthetic lab"), [])
        self.assertIn("native history", forgotten["retained"])

    def test_reader_cannot_write_and_project_grant_excludes_hot_memory(self):
        personal = self.remember("PREFERENCE: prefer concise answers", "personal", "principal")
        self.assertEqual(personal["status"], "committed")
        self.assertEqual(self.memory.recall(READER, "concise"), [])
        result = self.memory.remember(READER, category="project", content="A prohibited change.",
                                      title="Denied", project="lab", request_id="denied")
        self.assertEqual(result["status"], "rejected")

    def test_invalid_hot_entry_is_not_reported_saved(self):
        result = self.remember("RULE: " + "x" * 300, "too-long", "assistant")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.memory.recall(OWNER, "xxx"), [])

    def test_concurrent_native_writes_do_not_lose_acknowledged_facts(self):
        def save(number):
            return self.memory.remember(OWNER, category="principal", content=f"RULE: synthetic fact {number}",
                                        title="", project="", request_id=f"concurrent-{number}")
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(save, range(8)))
        self.assertTrue(all(result["status"] == "committed" for result in results), results)
        found = self.memory.recall(OWNER, "synthetic fact")
        self.assertEqual(len(found), 8)

    def test_reordered_hot_entries_keep_their_saved_reference(self):
        first = self.remember("RULE: first stable fact", "stable-one", "principal")
        self.remember("RULE: second stable fact", "stable-two", "principal")
        found = next(row for row in self.memory.recall(OWNER, "stable") if "first" in row["content"])
        self.assertEqual(first["reference"], found["reference"])

    def test_rejected_physical_user_boundary_is_explicit(self):
        (self.root / "LIFEOS/MEMORY").unlink()
        (self.root / "LIFEOS/MEMORY").mkdir()
        result = self.remember()
        self.assertEqual(result["status"], "rejected")
        self.assertIn("boundary", result["reason"].lower())


if __name__ == "__main__":
    unittest.main()
