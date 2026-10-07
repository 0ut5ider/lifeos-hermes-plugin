# ABOUTME: Checks the native LifeOS ISA write guard against real Docker file operations.
# ABOUTME: Confirms an external edit blocks a stale write and a fresh read clears it.

import json
import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from lifeos_hook_bridge.bridge import HookBridge


class LiveContainerISATests(unittest.TestCase):
    def test_container_read_external_edit_and_native_write_guard(self):
        image = os.environ.get("LIFEOS_DOCKER_PROBE_IMAGE")
        if not image:
            self.skipTest("disposable Docker image is required")

        from tools.environments.docker import DockerEnvironment
        from tools.file_tools import clear_file_ops_cache, read_file_tool
        from tools.terminal_tool import _active_environments, _env_lock

        bun_path = shutil.which("bun")
        if not bun_path:
            self.skipTest("Bun is required for the installed LifeOS hook")
        bun = Path(bun_path)
        hooks = Path.home() / ".claude/hooks"
        if not (hooks / "ISAStaleWriteGuard.hook.ts").exists():
            self.skipTest("installed LifeOS ISA hook and Bun are required")

        project = "/tmp/lifeos-container-isa-probe"
        path = f"{project}/ISA.md"
        session = f"container-isa-{uuid4().hex}"
        state = Path.home() / f".claude/LIFEOS/MEMORY/STATE/isa-session-view/{session}.json"
        env = DockerEnvironment(image=image, cwd=project, task_id="lifeos-container-isa-probe",
                                network=False, persistent_filesystem=False)
        with _env_lock:
            _active_environments["default"] = env
        try:
            initial = env.execute("mkdir -p . && cat > ISA.md", cwd=project,
                                  stdin_data="one\nold\n", timeout=20)
            self.assertEqual(initial["returncode"], 0, initial["output"])
            with TemporaryDirectory(prefix="container-isa-") as directory:
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
                    edit = env.execute("cat > ISA.md", cwd=project, stdin_data=changed, timeout=20)
                    self.assertEqual(edit["returncode"], 0, edit["output"])
                    verdict = bridge.pre_tool_call(
                        "write_file", {"path": path, "content": "one\nold\nmy edit\n"},
                        session_id=session, task_id="default",
                    )
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
            env.cleanup(force_remove=True)
            self.assertTrue(env.wait_for_cleanup(timeout=30))
