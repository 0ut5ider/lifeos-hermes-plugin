# ABOUTME: Exercises governed memory operations against real native LifeOS tools.
# ABOUTME: Uses isolated synthetic user data for retries, curation, permissions, and concurrency.

from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
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

    def test_hot_correction_validates_before_mutation(self):
        saved = self.remember("RULE: original synthetic marker", "original", "principal")
        for index, replacement in enumerate((
            "RULE: public <private>SYNTHETIC_DENIED_MARKER</private>",
            "RULE: first line\nsecond line",
            "RULE: " + "😀" * 129,
        )):
            with self.subTest(replacement=replacement):
                receipt = self.memory.correct(OWNER, saved["reference"], replacement, f"invalid-{index}")
                self.assertEqual(receipt["status"], "rejected")
                self.assertEqual(self.memory.recall(OWNER, "original")[0]["reference"], saved["reference"])
                self.assertEqual(self.memory.recall(OWNER, "DENIED_MARKER"), [])

    def test_correction_cannot_reactivate_forgotten_text(self):
        first = self.remember("Synthetic forgotten marker", "forgotten")
        self.memory.forget(OWNER, first["reference"], "forget")
        other = self.remember("Synthetic alternative marker", "other")
        result = self.memory.correct(OWNER, other["reference"], "Synthetic forgotten marker", "revive")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.memory.recall(OWNER, "forgotten"), [])

    def test_hot_project_metadata_cannot_create_aliases(self):
        first = self.remember("RULE: synthetic duplicate marker", "one", "principal")
        second = self.memory.remember(OWNER, category="principal", content="RULE: synthetic duplicate marker",
                                      title="", project="", request_id="two")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(second["reference"], first["reference"])
        self.memory.forget(OWNER, first["reference"], "forget-first")
        self.assertEqual(self.memory.recall(OWNER, "duplicate"), [])

    def test_correction_to_existing_hot_fact_keeps_one_reference(self):
        first = self.remember("RULE: synthetic alpha marker", "one", "principal")
        second = self.remember("RULE: synthetic beta marker", "two", "principal")
        result = self.memory.correct(OWNER, first["reference"], "RULE: synthetic beta marker", "merge")
        self.assertEqual(result["reference"], second["reference"])
        self.assertEqual(len(self.memory.recall(OWNER, "beta")), 1)
        self.memory.forget(OWNER, second["reference"], "forget-second")
        self.assertEqual(self.memory.recall(OWNER, "beta"), [])

    def test_changed_section_cannot_resolve_to_retained_quotations(self):
        first = self.remember("Synthetic section original marker", "one")
        note = next((self.root / "LIFEOS/MEMORY/KNOWLEDGE/Research").glob("*.md"))
        note.write_text(note.read_text().replace("Synthetic section original marker", "Synthetic section changed marker") +
                        "\n## Unrelated quotations\nSynthetic section original marker\nSynthetic section original marker\n")
        result = self.memory.correct(OWNER, first["reference"], "Synthetic replacement marker", "ambiguous")
        self.assertEqual(result["status"], "conflict")
        self.assertNotIn("Synthetic replacement marker", note.read_text())

    def test_reference_binds_body_when_title_contains_the_same_text(self):
        content = "Synthetic exact title marker"
        saved = self.memory.remember(OWNER, category="project", content=content, title=content,
                                     project="lab", request_id="title-body")
        note = next((self.root / "LIFEOS/MEMORY/KNOWLEDGE/Research").glob("*.md"))
        note.write_text(note.read_text().replace("\n" + content + "\n", "\nSynthetic changed body marker\n"))
        result = self.memory.correct(OWNER, saved["reference"], "Synthetic replacement marker", "stale-title")
        self.assertEqual(result["status"], "conflict")
        self.assertNotIn("Synthetic replacement marker", note.read_text())

    def test_interrupted_native_publication_recovers_before_retry(self):
        script = '''import os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory = NativeMemory(Path(sys.argv[1]))
def interrupt(*args, **kwargs):
    os._exit(73)
memory._record = interrupt
memory.remember(OWNER, category="project", content="Synthetic crash marker", title="Crash recovery",
                project="lab", request_id="crash")
'''
        child = subprocess.run([sys.executable, "-c", script, str(self.root)], capture_output=True, text=True)
        self.assertEqual(child.returncode, 73, child.stderr)
        arguments = dict(category="project", content="Synthetic crash marker", title="Crash recovery", project="lab")
        retry = self.memory.remember(OWNER, request_id="crash", **arguments)
        self.assertEqual(retry["status"], "committed", retry)
        self.assertEqual(len(self.memory.recall(OWNER, "crash")), 1)
        note = next((self.root / "LIFEOS/MEMORY/KNOWLEDGE/Research").glob("*.md"))
        self.assertEqual(note.read_text().count("Synthetic crash marker"), 1)

    def test_conflict_retry_reports_the_same_outcome(self):
        first = self.remember("Synthetic section original marker", "one")
        note = next((self.root / "LIFEOS/MEMORY/KNOWLEDGE/Research").glob("*.md"))
        note.write_text(note.read_text().replace("original", "changed"))
        arguments = (OWNER, first["reference"], "Synthetic replacement marker", "conflict-retry")
        first_result = self.memory.correct(*arguments)
        self.assertEqual(first_result["status"], "conflict")
        self.assertEqual(self.memory.correct(*arguments), first_result)

    def test_private_title_is_rejected_before_native_routing(self):
        saved = self.memory.remember(OWNER, category="project", content="Synthetic title routing marker",
                                     title="<private>hidden</private>Visible", project="lab", request_id="private-title")
        self.assertEqual(saved["status"], "rejected", saved)
        self.assertEqual(list((self.root / "LIFEOS/MEMORY").rglob("visible.md")), [])

    def test_crash_before_journal_cannot_leave_an_unknown_reservation(self):
        script = '''import os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory = NativeMemory(Path(sys.argv[1]))
memory.transaction.prepare = lambda *args, **kwargs: os._exit(73)
memory.remember(OWNER, category="project", content="Synthetic recovery marker", title="Recovery ordering",
                project="lab", request_id="before-prepare")
'''
        child = subprocess.run([sys.executable, "-c", script, str(self.root)], capture_output=True, text=True)
        self.assertEqual(child.returncode, 73, child.stderr)
        result = self.memory.remember(OWNER, category="project", content="Synthetic recovery marker",
                                     title="Recovery ordering", project="lab", request_id="before-prepare")
        self.assertEqual(result["status"], "committed", result)

    def test_changed_section_cannot_keep_an_obsolete_prefix_active(self):
        content = "The synthetic lab uses port 9123"
        saved = self.remember(content, "body-extension")
        note = next((self.root / "LIFEOS/MEMORY/KNOWLEDGE/Research").glob("*.md"))
        note.write_text(note.read_text().replace(content, content + " is obsolete; use port 9443."))
        result = self.memory.correct(OWNER, saved["reference"], "The synthetic lab uses port 9555", "extended")
        self.assertEqual(result["status"], "conflict")

    def test_native_child_holds_recovery_lock_after_parent_dies(self):
        saved = self.remember("RULE: synthetic original", "original", "principal")
        ready, gate, done = (self.home / name for name in ("ready", "continue", "done"))
        worker = self.home / "gated-native.ts"
        worker.write_text('''// ABOUTME: Pauses a real native writer for the parent-crash fixture.
// ABOUTME: Keeps publication inside the child that inherits the recovery lock.
import { existsSync, writeFileSync } from "node:fs";
const request = JSON.parse(await Bun.stdin.text());
writeFileSync(READY, "ready");
while (!existsSync(GATE)) await Bun.sleep(10);
const writer = await import(process.argv[2] + "/LIFEOS/TOOLS/MemoryWriter.ts");
const result = writer.setEntries(request.path, request.entries, {updatedBy: request.writer, allowDrastic: request.allowDrastic});
writeFileSync(DONE, JSON.stringify(result));
process.stdout.write(JSON.stringify(result));
'''.replace("READY", json.dumps(str(ready))).replace("GATE", json.dumps(str(gate))).replace("DONE", json.dumps(str(done))))
        script = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory = NativeMemory(Path(sys.argv[1]))
original = memory._native
def native(action, **values):
    if action == "set_hot": memory.worker = Path(WORKER)
    return original(action, **values)
memory._native = native
memory.correct(OWNER, REFERENCE, "RULE: synthetic orphan correction", "orphan")
'''.replace("WORKER", repr(str(worker))).replace("REFERENCE", repr(saved["reference"]))
        process = subprocess.Popen([sys.executable, "-c", script, str(self.root)], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        def wait_file(path):
            deadline = time.monotonic() + 10
            while not path.exists():
                if time.monotonic() >= deadline:
                    self.fail(f"Timed out waiting for {path.name}")
                time.sleep(0.01)
        try:
            wait_file(ready)
            process.kill()
            process.wait(timeout=5)
            with (self.memory.database.parent / "memory-access.lock").open("rb") as lock:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            gate.write_text("continue")
            wait_file(done)
            self.assertTrue(json.loads(done.read_text())["ok"])
            self.assertEqual(self.memory.recall(OWNER, "synthetic")[0]["reference"], saved["reference"])
            later = self.remember("RULE: synthetic acknowledged later", "later", "principal")
            self.assertEqual(later["status"], "committed")
            self.assertEqual(len(self.memory.recall(OWNER, "synthetic")), 2)
        finally:
            gate.write_text("continue")
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
