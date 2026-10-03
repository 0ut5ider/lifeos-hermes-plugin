# ABOUTME: Tests shared memory tool semantics with native synthetic LifeOS records.
# ABOUTME: Verifies server-bound grants, disabled sharing, and revocation on an open service.

import json
from pathlib import Path
import unittest

from lifeos_hook_bridge.memory_service import MemoryService, MemoryConfiguration
import test_memory_native as native_fixture

OWNER = native_fixture.OWNER


class MemoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.home / "hermes/memory.json"
        self.configuration = {
            "version": 1, "root": str(self.fixture.root), "principal": "owner",
            "sharing_enabled": False, "accounts": {}, "destinations": {},
            "clients": {"research": {"enabled": True, "read": ["project"], "write": [],
                                      "projects": ["lab"], "model_route": "unknown"}},
        }
        MemoryConfiguration(self.config).save(self.configuration)
        self.service = MemoryService(MemoryConfiguration(self.config))

    def test_sharing_starts_disabled_and_caller_arguments_cannot_grant_access(self):
        self.fixture.remember()
        result = self.service.call_client("research", "lifeos_memory_search", {"query": "synthetic lab"})
        self.assertEqual(result["status"], "rejected")
        result = self.service.call(OWNER, "lifeos_memory_search", {"query": "lab", "caller": "owner"})
        self.assertEqual(result["status"], "rejected")

    def test_client_reads_the_same_native_fact_and_revocation_applies_immediately(self):
        saved = self.fixture.remember()
        self.fixture.remember("RULE: synthetic private lab marker", "private", "principal")
        self.configuration["sharing_enabled"] = True
        MemoryConfiguration(self.config).save(self.configuration)
        first = self.service.call_client("research", "lifeos_memory_search", {"query": "synthetic lab"})
        self.assertEqual(first["status"], "ok")
        self.assertEqual(first["results"][0]["reference"], saved["reference"])
        self.assertNotIn("private", json.dumps(first))
        self.configuration["clients"]["research"]["enabled"] = False
        MemoryConfiguration(self.config).save(self.configuration)
        revoked = self.service.call_client("research", "lifeos_memory_get", {"reference": saved["reference"]})
        self.assertEqual(revoked["status"], "rejected")

    def test_project_write_grant_cannot_change_principal_memory(self):
        self.configuration["sharing_enabled"] = True
        self.configuration["clients"]["research"]["write"] = ["project"]
        MemoryConfiguration(self.config).save(self.configuration)
        arguments = {"category": "principal", "content": "RULE: unauthorized identity change", "title": "",
                     "project": "", "request_id": "identity"}
        denied = self.service.call_client("research", "lifeos_memory_remember", arguments)
        self.assertEqual(denied["status"], "rejected")
        arguments.update(category="project", content="Synthetic shared finding", title="Shared finding", project="lab")
        saved = self.service.call_client("research", "lifeos_memory_remember", arguments)
        self.assertEqual(saved["status"], "committed", saved)
        self.assertEqual(self.fixture.memory.recall(OWNER, "shared finding")[0]["reference"], saved["reference"])

    def test_get_obeys_current_revision_and_category_grants(self):
        saved = self.fixture.remember()
        corrected = self.fixture.memory.correct(OWNER, saved["reference"], "Synthetic updated project fact", "correct")
        stale = self.service.call(OWNER, "lifeos_memory_get", {"reference": saved["reference"]})
        self.assertEqual(stale["status"], "conflict")
        current = self.service.call(OWNER, "lifeos_memory_get", {"reference": corrected["reference"]})
        self.assertEqual(current["content"], "Synthetic updated project fact")

    def test_configuration_is_private_and_rejects_identity_write_enrollment(self):
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.configuration["clients"]["research"]["write"] = ["principal"]
        with self.assertRaises(ValueError):
            MemoryConfiguration(self.config).save(self.configuration)


if __name__ == "__main__":
    unittest.main()
