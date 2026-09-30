# ABOUTME: Verifies installed native APIs delegate through the governed memory service.
# ABOUTME: Runs real Bun and Python subprocesses with synthetic, app-neutral contexts.

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from datetime import datetime, timezone

from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native_fixture


class MemoryDelegationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.configuration = MemoryConfiguration(self.fixture.home / "memory.json")
        self.configuration.save({"version": 1, "root": str(self.root), "principal": "owner", "sharing_enabled": False,
                                 "accounts": {"chat-a:100": "owner"}, "destinations": {"chat-a:200": {
                                     "visibility": "private", "participants": ["owner"], "read": ["principal", "assistant", "project"],
                                     "write": ["principal", "assistant", "project"], "model_routes": ["local"], "projects": ["*"]}}})
        self.context = SessionContext("chat-a", "100", "200", "private", ("owner",), "local", "native-session")
        connector = self.root / "LIFEOS/USER/CONFIG/memory-access.json"
        connector.parent.mkdir()
        connector.write_text(json.dumps({"version": 1, "command": [sys.executable, str(Path(__file__).resolve().parents[1] /
                                                                                         "lifeos_hook_bridge/memory_rpc.py"),
                                                                  "--configuration", str(self.configuration.path)]}))
        connector.chmod(0o600)

    def call(self, operations, *, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL="1")
        environment.pop("LIFEOS_MEMORY_INTERNAL", None)
        environment.pop("LIFEOS_MEMORY_CONTEXT", None)
        if context:
            environment["LIFEOS_MEMORY_CONTEXT"] = json.dumps(asdict(self.context))
        result = subprocess.run([self.fixture.memory.bun, "--no-install", str(Path(__file__).with_name("native_memory_calls.ts")), str(self.root)],
                                input=json.dumps(operations), text=True, capture_output=True, env=environment, cwd=self.root, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_native_add_shares_reference_and_recall_with_the_service(self):
        results = self.call([{"name": "add", "item": {"type": "memory", "actor": "principal", "content": "RULE: native delegated fact"}},
                             {"name": "rank", "query": "delegated fact"}])
        self.assertTrue(results[0]["ok"], results)
        self.assertIn("native delegated fact", results[1]["markdownBlock"])
        self.assertEqual(len(self.fixture.memory.recall(native_fixture.OWNER, "delegated fact")), 1)

    def test_missing_context_cannot_write_or_recall_private_memory(self):
        self.fixture.remember("RULE: private marker", "private", "principal")
        results = self.call([{"name": "add", "item": {"type": "memory", "actor": "principal", "content": "RULE: unauthorized"}},
                             {"name": "rank", "query": "private marker"}], context=False)
        self.assertFalse(results[0]["ok"])
        self.assertNotIn("private marker", json.dumps(results[1]))

    def test_native_reviewer_snapshot_rejects_a_later_full_overwrite(self):
        self.fixture.remember("RULE: original", "original", "principal")
        path = str(self.root / "LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md")
        results = self.call([{"name": "read", "path": path},
                             {"name": "add", "item": {"type": "memory", "actor": "principal", "content": "RULE: concurrent explicit fact"}},
                             {"name": "set", "path": path, "entries": ["RULE: original"]}])
        self.assertTrue(results[1]["ok"], results)
        self.assertFalse(results[2]["ok"], results)
        self.assertIn("revision", results[2]["message"])
        self.assertEqual(len(self.fixture.memory.recall(native_fixture.OWNER, "original fact")), 2)

    def test_native_functions_keep_their_unmanaged_behavior_without_a_connector(self):
        (self.root / "LIFEOS/USER/CONFIG/memory-access.json").unlink()
        result = self.call([{"name": "add", "item": {"type": "memory", "actor": "principal", "content": "RULE: unmanaged fact"}},
                            {"name": "rank", "query": "unmanaged fact"}], context=False)
        self.assertTrue(result[0]["ok"], result)
        self.assertIn("unmanaged fact", result[1]["markdownBlock"])

    def test_native_full_curation_saves_new_entries_after_its_own_read(self):
        self.fixture.remember("RULE: original", "original", "principal")
        path = str(self.root / "LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md")
        result = self.call([{"name": "read", "path": path}, {"name": "add", "item": {"type": "memory", "actor": "principal",
                            "op": "set", "entries": ["RULE: original", "RULE: new reviewer fact"]}}])
        self.assertTrue(result[1]["ok"], result)
        self.assertEqual(len(self.fixture.memory.recall(native_fixture.OWNER, "original reviewer")), 2)

    def test_native_loader_excludes_hot_memory_without_an_approved_context(self):
        self.fixture.remember("RULE: private hot marker", "private-hot", "principal")
        denied = self.call([{"name": "load"}], context=False)
        self.assertNotIn("private hot marker", json.dumps(denied))
        allowed = self.call([{"name": "load"}])
        self.assertIn("private hot marker", allowed[0])

    def test_native_reviewer_excludes_sources_that_predate_a_correction(self):
        saved = self.fixture.remember("RULE: superseded marker", "original", "principal")
        corrected = self.fixture.memory.correct(native_fixture.OWNER, saved["reference"], "RULE: current marker", "correction")
        self.assertEqual(corrected["status"], "committed", corrected)
        prompt = self.call([{"name": "review_prompt", "exchanges": [{"ts": "2000-01-01T00:00:00Z",
                            "user": "superseded marker", "assistant": "Another paraphrase of the previous rule"}]}])[0]
        self.assertNotIn("superseded marker", prompt)
        self.assertNotIn("Another paraphrase", prompt)
        self.assertIn("current marker", prompt)

    def test_native_reviewer_excludes_a_recent_quote_of_a_forgotten_fact(self):
        saved = self.fixture.remember("RULE: forgotten native marker", "original", "principal")
        self.fixture.memory.forget(native_fixture.OWNER, saved["reference"], "forget")
        prompt = self.call([{"name": "review_prompt", "exchanges": [{"ts": datetime.now(timezone.utc).isoformat(),
                            "user": "Older transcript said forgotten native marker but that should stay forgotten", "assistant": "OK"}]}])[0]
        self.assertNotIn("forgotten native marker", prompt)

    def test_project_only_reviewer_excludes_unlabeled_personal_history(self):
        self.fixture.remember("RULE: private history marker", "private", "principal")
        configuration = self.configuration.load()
        grant = configuration["destinations"]["chat-a:200"]
        grant["read"], grant["write"] = ["project"], ["project"]
        self.configuration.save(configuration)
        prompt = self.call([{"name": "review_prompt", "exchanges": [{"ts": datetime.now(timezone.utc).isoformat(),
                            "user": "An older private note contains private history marker", "assistant": "Keep it"}]}])[0]
        self.assertNotIn("private history marker", prompt)


if __name__ == "__main__":
    unittest.main()
