# ABOUTME: Verifies native archive routing, stable references, and correction recovery.
# ABOUTME: Covers native link updates, private entities, ideas, and hot-entry presentation changes.

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_policy import MemoryScope
import test_memory_native as native_fixture


class MemoryArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.scope = native_fixture.OWNER

    def test_related_link_update_preserves_all_earlier_section_references(self):
        item = {"type": "knowledge", "entity_type": "research", "name": "Linked fixture", "content": "Original linked fact"}
        first = self.memory.native_add(self.scope, item, request_id="first", project="lab")
        second = self.memory.native_add(self.scope, {**item, "content": "Second linked fact",
                                                   "related": [{"slug": "synthetic-target", "type": "related"}]}, request_id="second", project="lab")
        self.assertTrue(second["ok"], second)
        self.assertEqual(self.memory.get(self.scope, first["receipt"]["reference"])["content"], item["content"])
        self.assertEqual(len(self.memory.recall(self.scope, "linked fact")), 2)

    def test_person_correction_recovers_the_same_native_archive_path(self):
        item = {"type": "knowledge", "entity_type": "person", "name": "Fictional Person", "content": "Original fictional fact"}
        first = self.memory.native_add(self.scope, item, request_id="first", project="lab")
        reference = first["receipt"]["reference"]
        script = """import os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory=NativeMemory(Path(sys.argv[1]))
memory._record=lambda *args,**kwargs: os._exit(73)
memory.correct(OWNER, REFERENCE, 'Corrected fictional fact', 'correct')
""".replace("REFERENCE", repr(reference))
        child = subprocess.run([sys.executable, "-c", script, str(self.fixture.root)], capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 73, child.stderr)
        self.assertEqual(self.memory.get(self.scope, reference)["content"], item["content"])
        paths = list((self.fixture.root / "LIFEOS/MEMORY/KNOWLEDGE").rglob("*.md"))
        self.assertEqual(paths, [Path(first["path"])])
        self.assertNotIn("Corrected fictional fact", paths[0].read_text())
        corrected = self.memory.correct(self.scope, reference, "Corrected fictional fact", "correct")
        self.assertEqual(corrected["status"], "committed", corrected)
        self.assertEqual(paths[0].read_text().count("Corrected fictional fact"), 1)

    def test_native_ideas_keep_their_retrieval_type(self):
        saved = self.memory.native_add(self.scope, {"type": "idea", "title": "Native fixture idea", "content": "Native idea marker"},
                                       request_id="idea", project="lab")
        self.assertTrue(saved["ok"], saved)
        self.assertEqual(len(self.memory.relevant_context(self.scope, "idea marker", {"typeFilter": "idea"})["results"]), 1)
        self.assertEqual(self.memory.relevant_context(self.scope, "idea marker", {"typeFilter": "knowledge"})["results"], [])

    def test_project_client_cannot_read_native_private_entity_notes(self):
        saved = self.memory.native_add(self.scope, {"type": "knowledge", "entity_type": "person", "name": "Fictional Person",
                                                   "content": "Private fictional marker"}, request_id="private", project="lab")
        self.assertTrue(saved["ok"], saved)
        self.assertEqual(self.memory.recall(native_fixture.READER, "fictional marker"), [])
        self.assertEqual(self.memory.get(native_fixture.READER, saved["receipt"]["reference"])["status"], "rejected")

    def test_presentation_change_keeps_one_current_identity_without_a_tombstone(self):
        first = self.fixture.remember("RULE: original retained fact", "first", "principal")
        observed = self.memory.read_hot(self.scope, "principal")
        changed = self.memory.native_set(self.scope, "principal", ["PREFERENCE: Original retained fact ~inferred"], "set", observed["revision"])
        self.assertTrue(changed["ok"], changed)
        current = self.memory.recall(self.scope, "retained fact")[0]
        self.assertEqual(current["reference"]["id"], first["reference"]["id"])
        self.assertEqual(current["reference"]["revision"], 2)
        filtered = self.memory.filter_history(self.scope, "Today confirms original retained fact", datetime.now(timezone.utc).isoformat())
        self.assertFalse(filtered["excluded"], filtered)
        self.assertEqual(self.fixture.remember(current["content"], "again", "principal")["status"], "unchanged")

    def test_project_duplicate_save_and_correction_keep_accessible_public_references(self):
        private = self.memory.native_add(self.scope, {"type": "knowledge", "entity_type": "person", "name": "Private Person",
                                                     "content": "Matching candidate fact"}, request_id="private", project="lab")
        writer = MemoryScope("client", "mcp:writer", ("project",), ("project",), ("lab",), "writer-test")
        public = self.memory.remember(writer, category="project", content="Matching candidate fact", title="Public record",
                                      project="lab", request_id="public")
        self.assertEqual(public["status"], "committed", public)
        self.assertNotEqual(public["reference"], private["receipt"]["reference"])
        self.assertEqual(self.memory.get(writer, public["reference"])["status"], "ok")
        other = self.memory.remember(writer, category="project", content="Original accessible fact", title="Other public record",
                                     project="lab", request_id="other")
        corrected = self.memory.correct(writer, other["reference"], "Matching candidate fact", "correct-other")
        self.assertEqual(corrected["status"], "committed", corrected)
        self.assertEqual(self.memory.get(writer, corrected["reference"])["status"], "ok")


if __name__ == "__main__":
    unittest.main()
