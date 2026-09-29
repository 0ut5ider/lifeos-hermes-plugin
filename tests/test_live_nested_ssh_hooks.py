# ABOUTME: Verifies nested Hermes tool and LifeOS hook delivery over a real SSH backend.
# ABOUTME: Uses a disposable file below the supplied SSH project root.

import json
import os
import shlex
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


class LiveNestedSshHookTests(unittest.TestCase):
    def test_execute_code_inner_read_uses_ssh_workspace_and_outer_session(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.code_execution_tool import execute_code
        from tools.code_kernel import shutdown_all_kernels
        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_scope import reset_terminal_scope, set_terminal_scope
        from tools.terminal_tool import _active_environments, _env_lock

        session = f"lifeos-nested-ssh-{uuid4().hex}"
        name = f"nested-{uuid4().hex}.txt"
        path = f"{project.rstrip('/')}/{name}"
        env = SSHEnvironment(host=host, user=user, cwd=project,
                             key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        token = set_terminal_scope({"TERMINAL_ENV": "ssh"})
        try:
            with patch.dict(os.environ, {"TERMINAL_ENV": "ssh"}):
                prepared = env.execute(f"printf NESTED_SSH_READY > {shlex.quote(path)}",
                                       cwd=project, timeout=20)
                self.assertEqual(prepared["returncode"], 0, prepared["output"])
                source = "import hermes_tools\n" + f"print(hermes_tools.read_file(path={path!r}))\n"
                result = json.loads(execute_code(source, task_id="default", session_id=session,
                                                 enabled_tools=["read_file"]))
            self.assertEqual(result["status"], "success", result)
            self.assertIn("NESTED_SSH_READY", json.dumps(result))
            lifeos_dir = Path(os.environ.get("LIFEOS_DIR", Path.home() / ".claude/LIFEOS"))
            transcript = (lifeos_dir / "MEMORY/STATE/hermes-transcripts"
                          / f"{session}.jsonl")
            self.assertTrue(transcript.exists(), session)
            rows = [json.loads(line) for line in transcript.read_text().splitlines()]
            names = [item.get("name") for row in rows if row.get("type") == "assistant"
                     for item in row.get("message", {}).get("content", [])
                     if isinstance(item, dict) and item.get("type") == "tool_use"]
            self.assertIn("Read", names)
        finally:
            reset_terminal_scope(token)
            shutdown_all_kernels()
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.execute(f"rm -f {shlex.quote(path)}", cwd=project, timeout=20)
            env.cleanup()


if __name__ == "__main__":
    unittest.main()
