# ABOUTME: Checks native Bash permission routing through the real SSH terminal backend.
# ABOUTME: Uses an explicit disposable SSH project and removes its hook files afterward.

import json
import os
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SAFETY_HOOK = os.environ.get("LIFEOS_PERMISSION_HOOK")
SSH_HOST = os.environ.get("LIFEOS_SSH_PROBE_HOST")
SSH_USER = os.environ.get("LIFEOS_SSH_PROBE_USER")
SSH_KEY = os.environ.get("LIFEOS_SSH_PROBE_KEY")
SSH_PROJECT = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")


@unittest.skipUnless(
    all((SAFETY_HOOK, SSH_HOST, SSH_USER, SSH_KEY, SSH_PROJECT)),
    "native Safety hook and disposable SSH project are required",
)
class LiveSshCommandPolicyTests(unittest.TestCase):
    def test_project_permission_denial_uses_ssh_workspace(self):
        from hermes_cli import plugins as plugins_mod
        from tools import terminal_tool as terminal_module

        task_id = f"lifeos-ssh-policy-{uuid4().hex}"
        marker = f"{SSH_PROJECT.rstrip('/')}/permission-invoked-{uuid4().hex}"
        project_settings_path = f"{SSH_PROJECT.rstrip('/')}/.claude/settings.local.json"
        with tempfile.TemporaryDirectory(prefix="lifeos-ssh-policy-") as directory:
            root = Path(directory)
            home = root / "hermes"
            plugin = home / "plugins/lifeos-hook-bridge"
            plugin.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "lifeos_hook_bridge", plugin)
            (home / "config.yaml").write_text(
                "plugins:\n  enabled:\n    - lifeos-hook-bridge\napprovals:\n  mode: manual\n"
            )
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"PermissionRequest": [{
                "matcher": "Bash", "hooks": [{"type": "command", "command": SAFETY_HOOK}],
            }]}}))
            trust = root / "remote-projects.json"
            trust.write_text(json.dumps({"projects": [{
                "type": "ssh", "host": SSH_HOST, "user": SSH_USER, "port": 22, "root": SSH_PROJECT,
            }]}))
            environment = {
                "HERMES_HOME": str(home),
                "LIFEOS_HOOK_SETTINGS": str(settings),
                "LIFEOS_DIR": str(root / "LIFEOS"),
                "LIFEOS_REMOTE_PROJECT_TRUST": str(trust),
                "HERMES_INTERACTIVE": "1",
                "TERMINAL_ENV": "ssh",
                "TERMINAL_SSH_HOST": SSH_HOST,
                "TERMINAL_SSH_USER": SSH_USER,
                "TERMINAL_SSH_KEY": SSH_KEY,
                "TERMINAL_CWD": "/tmp",
                "PATH": str(Path.home() / ".bun/bin") + os.pathsep + os.environ.get("PATH", ""),
            }
            prompts = []
            remote = None
            with patch.dict(os.environ, environment):
                plugins_mod._reset_plugin_managers_for_tests()
                previous_callback = terminal_module._get_approval_callback()
                with terminal_module._env_lock:
                    previous_environments = set(terminal_module._active_environments)
                terminal_module.set_approval_callback(
                    lambda *args, **kwargs: prompts.append(args) or "deny"
                )
                try:
                    first = json.loads(terminal_module.terminal_tool(
                        "curl -I --max-time 1 http://192.168.8.1:9", task_id=task_id, timeout=20,
                    ))
                    self.assertEqual(first["status"], "blocked", first)
                    self.assertEqual(len(prompts), 1)

                    with terminal_module._env_lock:
                        environment_key = terminal_module._resolve_container_task_id(task_id)
                        self.assertIn(environment_key, terminal_module._active_environments)
                        remote = terminal_module._active_environments[environment_key]
                    absent = remote.execute(
                        f"test ! -e {shlex.quote(project_settings_path)}", cwd=SSH_PROJECT, timeout=20,
                    )
                    self.assertEqual(absent["returncode"], 0, absent)
                    hook = "sh -c " + shlex.quote(f"printf hit > {shlex.quote(marker)}; exit 2")
                    project_settings = {"hooks": {"PermissionRequest": [{
                        "matcher": "Bash", "hooks": [{"type": "command", "command": hook}],
                    }]}}
                    written = remote.execute(
                        f"cat > {shlex.quote(project_settings_path)}", cwd=SSH_PROJECT,
                        stdin_data=json.dumps(project_settings), timeout=20,
                    )
                    self.assertEqual(written["returncode"], 0, written)
                    plugins_mod._reset_plugin_managers_for_tests()
                    second = json.loads(terminal_module.terminal_tool(
                        "curl -I --max-time 1 http://192.168.8.1:9", task_id=task_id,
                        workdir=SSH_PROJECT, timeout=20,
                    ))
                    self.assertEqual(second["status"], "blocked", second)
                    self.assertEqual(len(prompts), 1, "Project denial must not ask for human approval")
                    observed = remote.execute(f"cat {shlex.quote(marker)}", cwd=SSH_PROJECT, timeout=20)
                    self.assertEqual(observed["output"], "hit", observed)
                finally:
                    terminal_module.set_approval_callback(previous_callback)
                    plugins_mod._reset_plugin_managers_for_tests()
                    if remote is not None:
                        remote.execute(
                            f"rm -f {shlex.quote(marker)} {shlex.quote(project_settings_path)}",
                            cwd=SSH_PROJECT, timeout=20,
                        )
                    with terminal_module._env_lock:
                        added_keys = set(terminal_module._active_environments) - previous_environments
                        environments = [terminal_module._active_environments.pop(key) for key in added_keys]
                    for item in {id(value): value for value in environments}.values():
                        item.cleanup()


if __name__ == "__main__":
    unittest.main()
