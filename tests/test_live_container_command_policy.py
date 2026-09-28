# ABOUTME: Checks the native LifeOS Bash policy through Hermes's real Docker terminal tool.
# ABOUTME: Uses a disposable plugin home and removes the test container after each run.

import json
import hashlib
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("LIFEOS_DOCKER_PROBE_IMAGE")
SAFETY_HOOK = os.environ.get("LIFEOS_PERMISSION_HOOK")


@unittest.skipUnless(IMAGE and SAFETY_HOOK, "Docker image and native Safety hook are required")
class LiveContainerCommandPolicyTests(unittest.TestCase):
    def test_native_neutral_command_is_blocked_before_docker_execution(self):
        from hermes_cli import plugins as plugins_mod
        from tools import terminal_tool as terminal_module

        with tempfile.TemporaryDirectory(prefix="lifeos-docker-policy-") as directory:
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
            environment = {
                "HERMES_HOME": str(home),
                "LIFEOS_HOOK_SETTINGS": str(settings),
                "LIFEOS_DIR": str(root / "LIFEOS"),
                "LIFEOS_REMOTE_PROJECT_TRUST": str(root / "remote-projects.json"),
                "HERMES_INTERACTIVE": "1",
                "TERMINAL_ENV": "docker",
                "TERMINAL_DOCKER_IMAGE": IMAGE,
                "TERMINAL_DOCKER_NETWORK": "false",
                "TERMINAL_DOCKER_RUN_AS_HOST_USER": "true",
                "TERMINAL_CONTAINER_PERSISTENT": "false",
                "TERMINAL_DOCKER_PERSIST_ACROSS_PROCESSES": "false",
                "TERMINAL_CWD": "/tmp",
                "PATH": str(Path.home() / ".bun/bin") + os.pathsep + os.environ.get("PATH", ""),
            }
            task_id = f"lifeos-command-policy-{uuid4().hex}"
            prompts = []
            with patch.dict(os.environ, environment):
                plugins_mod._reset_plugin_managers_for_tests()
                previous_callback = terminal_module._get_approval_callback()
                with terminal_module._env_lock:
                    previous_environments = set(terminal_module._active_environments)
                terminal_module.set_approval_callback(
                    lambda *args, **kwargs: prompts.append(args) or "deny"
                )
                try:
                    result = json.loads(terminal_module.terminal_tool(
                        "curl -I http://192.168.8.1:9", task_id=task_id, timeout=20,
                    ))
                    self.assertEqual(result["status"], "blocked", result)
                    self.assertEqual(len(prompts), 1)
                    self.assertIn("curl -I http://192.168.8.1:9", " ".join(prompts[0]))

                    allowed = json.loads(terminal_module.terminal_tool(
                        "echo 67890", task_id=task_id, timeout=20,
                    ))
                    self.assertEqual(allowed["exit_code"], 0, allowed)
                    self.assertIn("67890", json.dumps(allowed))
                    self.assertEqual(len(prompts), 1)

                    log = root / "LIFEOS/MEMORY/OBSERVABILITY/permission-decisions.jsonl"
                    decisions = [json.loads(line)["decision"] for line in log.read_text().splitlines()]
                    self.assertEqual(decisions, ["neutral", "allow"])

                    with terminal_module._env_lock:
                        added_keys = set(terminal_module._active_environments) - previous_environments
                        self.assertIn(task_id, added_keys)
                        container = terminal_module._active_environments[task_id]
                    image_id = subprocess.run(
                        [container._docker_exe, "inspect", "--format", "{{.Image}}", container._container_id],
                        capture_output=True, text=True, check=True, timeout=20,
                    ).stdout.strip()
                    (root / "remote-projects.json").write_text(json.dumps({"projects": [{
                        "type": "docker", "image_id": image_id, "root": "/tmp",
                    }]}))
                    marker = "/tmp/lifeos-permission-project-invoked"
                    project_hook = "sh -c " + shlex.quote(f"printf hit > {marker}; exit 2")
                    project_settings = {"hooks": {"PermissionRequest": [{
                        "matcher": "Bash", "hooks": [{"type": "command", "command": project_hook}],
                    }]}}
                    prepared = container.execute(
                        "mkdir -p .claude && cat > .claude/settings.json", cwd="/tmp",
                        stdin_data=json.dumps(project_settings), timeout=20,
                    )
                    self.assertEqual(prepared["returncode"], 0, prepared)
                    result = json.loads(terminal_module.terminal_tool(
                        "curl -I http://192.168.8.1:9", task_id=task_id, timeout=20,
                    ))
                    self.assertEqual(result["status"], "blocked", result)
                    self.assertEqual(len(prompts), 1, "Project denial must not ask for human approval")
                    observed = container.execute(f"cat {marker}", cwd="/tmp", timeout=20)
                    self.assertEqual(observed["output"], "hit", observed)
                    project_settings = {"permissions": {"deny": ["Bash(printf world)"]}}
                    prepared = container.execute(
                        "cat > .claude/settings.json", cwd="/tmp",
                        stdin_data=json.dumps(project_settings), timeout=20,
                    )
                    self.assertEqual(prepared["returncode"], 0, prepared)
                    plugins_mod._reset_plugin_managers_for_tests()
                    compound = json.loads(terminal_module.terminal_tool(
                        "printf hello; printf world", task_id=task_id, workdir="/tmp", timeout=20,
                    ))
                    self.assertEqual(compound["status"], "blocked", compound)
                    self.assertEqual(len(prompts), 1, "Project deny must not ask for approval")
                    skill_path = "/tmp/.claude/skills/research/SKILL.md"
                    prepared = container.execute(
                        "mkdir -p .claude/skills/research && printf 'remote skill' > .claude/skills/research/SKILL.md",
                        cwd="/tmp", timeout=20,
                    )
                    self.assertEqual(prepared["returncode"], 0, prepared)
                    from lifeos_hook_bridge.bridge import HookBridge
                    scan = HookBridge._remote_skill_fingerprints(
                        SimpleNamespace(root="/tmp", backend=container),
                    )
                    self.assertEqual(scan[skill_path], hashlib.sha256(b"remote skill").hexdigest())
                finally:
                    terminal_module.set_approval_callback(previous_callback)
                    plugins_mod._reset_plugin_managers_for_tests()
                    with terminal_module._env_lock:
                        added_keys = set(terminal_module._active_environments) - previous_environments
                        environments = [terminal_module._active_environments.pop(key) for key in added_keys]
                    for item in {id(value): value for value in environments}.values():
                        item.cleanup(force_remove=True)
                        self.assertTrue(item.wait_for_cleanup(timeout=30))


if __name__ == "__main__":
    unittest.main()
