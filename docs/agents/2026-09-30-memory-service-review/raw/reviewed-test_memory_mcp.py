# ABOUTME: Exercises the optional memory server through a real MCP stdio connection.
# ABOUTME: Verifies shared native references, denied writes, and live connection revocation.

import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

import test_memory_native as native_fixture
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class MemoryMCPTests(unittest.TestCase):
    def test_installed_server_obeys_credential_grants_and_revocation(self):
        fixture = native_fixture.NativeMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        installed = fixture.home / "plugins/lifeos-hook-bridge"
        shutil.copytree(Path(__file__).resolve().parents[1] / "lifeos_hook_bridge", installed,
                        ignore=shutil.ignore_patterns("__pycache__"))
        saved = fixture.remember()
        fixture.remember("RULE: synthetic forbidden lab preference", "private", "principal")
        configuration = {"version": 1, "root": str(fixture.root), "principal": "owner",
                         "sharing_enabled": True, "accounts": {}, "destinations": {},
                         "clients": {"reader": {"enabled": True, "read": ["project"], "write": [],
                                                "projects": ["lab"], "model_route": "unknown"}}}
        path = fixture.home / "hermes/memory.json"
        MemoryConfiguration(path).save(configuration)
        parameters = StdioServerParameters(command=sys.executable,
                                          args=[str(installed / "memory_mcp.py"), "--configuration", str(path), "--client", "reader"])
        async def exercise():
            with tempfile.TemporaryFile(mode="w+") as errors:
                async with Client(stdio_client(parameters, errlog=errors), cache=None) as client:
                    listed = await client.list_tools()
                    names = {tool.name for tool in listed.tools}
                    self.assertIn("lifeos_memory_correct", names)
                    result = await client.call_tool("lifeos_memory_search", {"query": "synthetic lab"})
                    body = result.structured_content
                    self.assertEqual(body["results"][0]["reference"], saved["reference"])
                    self.assertNotIn("forbidden", json.dumps(body))
                    denied = await client.call_tool("lifeos_memory_remember", {
                        "category": "project", "content": "Prohibited write", "title": "Denied", "project": "lab", "request_id": "denied",
                    })
                    self.assertEqual(denied.structured_content["status"], "rejected")
                    configuration["clients"]["reader"]["enabled"] = False
                    MemoryConfiguration(path).save(configuration)
                    revoked = await client.call_tool("lifeos_memory_get", {"reference": saved["reference"]})
                    self.assertEqual(revoked.structured_content["status"], "rejected")
                errors.seek(0)
                self.assertEqual(errors.read(), "")
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
