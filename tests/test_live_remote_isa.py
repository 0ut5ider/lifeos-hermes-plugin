# ABOUTME: Checks the bridge and native ISA guard against a disposable SSH backend.
# ABOUTME: Runs only when a test SSH target and isolated ISA path are supplied.

import json
import os
import shlex
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from lifeos_hook_bridge.bridge import HookBridge


class LiveRemoteISATests(unittest.TestCase):
    def test_remote_read_external_edit_and_native_write_guard(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        path = os.environ.get("LIFEOS_SSH_PROBE_ISA")
        if not all((host, user, key, path)):
            self.skipTest("disposable SSH fixture is required")

        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache, read_file_tool
        from tools.terminal_tool import _active_environments, _env_lock

        bun = Path.home() / ".bun/bin/bun"
        hooks = Path.home() / ".claude/hooks"
        session = f"remote-isa-{uuid4().hex}"
        state = Path.home() / f".claude/LIFEOS/MEMORY/STATE/isa-session-view/{session}.json"
        env = SSHEnvironment(host=host, user=user, cwd=str(Path(path).parent),
                             key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        try:
            with TemporaryDirectory(prefix="live-remote-isa-") as directory:
                root = Path(directory)
                settings = root / "settings.json"
                settings.write_text(json.dumps({"hooks": {
                    "PostToolUse": [{"matcher": "Read", "hooks": [{"type": "command",
                        "command": f"{bun} {hooks / 'ISAStaleWriteGuard.hook.ts'}"}]}],
                    "PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command",
                        "command": f"{bun} {hooks / 'PreToolGuard.hook.ts'}"}]}],
                }}))
                bridge = HookBridge(settings, root)
                try:
                    first = read_file_tool(path, task_id="default")
                    self.assertFalse(json.loads(first).get("not_found"), first)
                    bridge.post_tool_call("read_file", {"path": path}, first,
                                          session_id=session, task_id="default")
                    self.assertTrue(state.exists())

                    changed = "one\nexternal edit\n"
                    edit = subprocess.run(
                        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
                         "-i", key, f"{user}@{host}",
                         f"printf 'one\\nexternal edit\\n' > {shlex.quote(path)}"],
                        capture_output=True, text=True, timeout=20,
                    )
                    self.assertEqual(edit.returncode, 0, edit.stderr)
                    verdict = bridge.pre_tool_call("write_file", {"path": path, "content": "one\nold\nmy edit\n"},
                                                   session_id=session, task_id="default")
                    self.assertEqual(verdict["action"], "block")
                    self.assertIn("stale whole-file Write", verdict["message"])

                    latest = read_file_tool(path, task_id="default")
                    self.assertFalse(json.loads(latest).get("not_found"), latest)
                    bridge.post_tool_call("read_file", {"path": path}, latest,
                                          session_id=session, task_id="default")
                    fresh = bridge.pre_tool_call("write_file", {"path": path, "content": changed},
                                                 session_id=session, task_id="default")
                    self.assertFalse(fresh and fresh.get("action") == "block", fresh)
                finally:
                    bridge.close()
        finally:
            state.unlink(missing_ok=True)
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup()


if __name__ == "__main__":
    unittest.main()
