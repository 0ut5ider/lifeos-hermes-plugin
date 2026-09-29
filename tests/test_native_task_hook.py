# ABOUTME: Exercises the optional Hermes count adapter in LifeOS TaskGovernance.
# ABOUTME: Set LIFEOS_TASK_HOOK_PATH to run against a patched LifeOS checkout.

import json
import os
import shutil
import subprocess
import tempfile
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.native_capabilities import RECORD_NAME, capability_record


HOOK_PATH = os.environ.get("LIFEOS_TASK_HOOK_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS hook and Bun are required")
class NativeTaskHookTests(unittest.TestCase):
    def test_discovery_does_not_dispatch_unrelated_creation_hooks(self):
        requests = []

        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"continue":true}')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
        worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "hooks/TaskGovernance.hook.ts"
            native.parent.mkdir()
            native.symlink_to(HOOK_PATH)
            (native.parent / RECORD_NAME).write_text(json.dumps(capability_record()))
            marker = root / "events.jsonl"
            recorder = root / "record.py"
            recorder.write_text(
                "import json,sys\nfrom pathlib import Path\n"
                f"with Path({str(marker)!r}).open('a') as out: out.write(json.dumps(json.load(sys.stdin))+'\\n')\n"
            )
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"TaskCreated": [{"hooks": [
                {"type": "command", "command": f"bun {native}"},
                {"type": "command", "command": f"{sys.executable} {recorder}"},
                {"type": "http", "url": f"http://127.0.0.1:{server.server_port}/task-created"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            try:
                self.assertTrue(bridge._supports_native_task_hook("probe", str(root)))
                self.assertFalse(marker.exists(), "Discovery delivered a synthetic creation event")
                self.assertEqual(requests, [], "Discovery delivered a synthetic HTTP creation event")
                self.assertIsNone(bridge._native_task_verdict(
                    "probe", "task-1", "Meaningful task", "Meaningful task description", 0))
                rows = [json.loads(row) for row in marker.read_text().splitlines()]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["task_id"], "task-1")
                self.assertNotIn("hermes_bridge_probe", rows[0])
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]["task_id"], "task-1")
            finally:
                bridge.close()

    def invoke(self, **fields):
        payload = {"hook_event_name": "TaskCreated", "session_id": "hermes-test", **fields}
        return subprocess.run(
            ["bun", HOOK_PATH], input=json.dumps(payload), text=True, capture_output=True, timeout=10,
        )

    def test_synthetic_probe_does_not_bypass_native_quality_gate(self):
        result = self.invoke(hermes_bridge_probe=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("description too short", result.stderr)

    def test_external_count_controls_limit_without_writing_legacy_counter(self):
        legacy = Path("/tmp/pai-task-governance.json")
        before = legacy.stat().st_mtime_ns if legacy.exists() else None
        accepted = self.invoke(task_description="Meaningful task description", hermes_task_count=49)
        denied = self.invoke(task_description="Meaningful task description", hermes_task_count=50)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(denied.returncode, 2)
        self.assertIn("session limit of 50", denied.stderr)
        after = legacy.stat().st_mtime_ns if legacy.exists() else None
        self.assertEqual(after, before)

    def test_short_description_blocks_with_external_count(self):
        result = self.invoke(task_description="short", hermes_task_count=0)
        self.assertEqual(result.returncode, 2)
        self.assertIn("description too short", result.stderr)
