# ABOUTME: Verifies that only an explicitly trusted SSH project can run its hooks.
# ABOUTME: Exercises the bridge against a disposable SSH project and real hook process.

import json
import os
import shlex
import subprocess
import sys
import time
import unittest
import threading
from uuid import uuid4
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


class LiveRemoteProjectHookTests(unittest.TestCase):
    def test_ssh_symlink_destination_file_rule(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_tool import _active_environments, _env_lock

        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        name = f"symlink-permission-{uuid4().hex}"
        secret = os.path.normpath(f"{project}/../{name}.txt")
        link = f"{project}/{name}.link"
        ordinary = f"{project}/{name}.ordinary"
        file_commands = (
            f"cat {name}.link", f"wc -c {name}.link", f"grep parity {name}.link",
            f"stat {name}.link", f"diff {name}.link {name}.ordinary",
            f"sort {name}.link", f"ls {name}.link", f"file {name}.link",
            f"find {name}.link -maxdepth 0",
            f"rg parity {name}.link", f"cut -c 1-6 {name}.link",
            f"awk '{{print $1}}' {name}.link",
        )
        try:
            setup = env.execute(
                f"printf '%s' parity > {shlex.quote(secret)} && "
                f"ln -s {shlex.quote(secret)} {shlex.quote(link)} && "
                f"printf '%s' ordinary > {shlex.quote(ordinary)}",
                cwd=project, timeout=20,
            )
            self.assertEqual(setup["returncode"], 0, setup)
            with TemporaryDirectory(prefix="remote-symlink-rule-") as directory:
                root = Path(directory)
                settings = root / "settings.json"
                settings.write_text(json.dumps({
                    "hooks": {},
                    "permissions": {
                        "allow": [*(f"Bash({command})" for command in file_commands),
                                  f"Bash(cat {name}.ordinary)"],
                        "deny": [f"Read(//{secret.lstrip('/')})"],
                    },
                }))
                trust = root / "remote-projects.json"
                trust.write_text('{"projects":[]}')
                with patch.dict(os.environ, {"LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}):
                    bridge = HookBridge(settings, root)
                try:
                    self.assertIsNone(bridge.command_approval(
                        f"cat {name}.ordinary", session_key="ssh-symlink", cwd=project, task_id="default",
                    ))
                    for command in file_commands:
                        with self.subTest(command=command):
                            self.assertEqual(bridge.command_approval(
                                command, session_key="ssh-symlink", cwd=project, task_id="default",
                            ), {"action": "deny"})
                    verdict = bridge.pre_tool_call(
                        "read_file", {"path": link}, session_id="ssh-symlink", task_id="default",
                    )
                    self.assertEqual(verdict["action"], "block")
                finally:
                    bridge.close()
        finally:
            env.execute(
                f"rm -f {shlex.quote(secret)} {shlex.quote(link)} {shlex.quote(ordinary)}",
                cwd=project, timeout=20,
            )
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup()

    def test_ssh_project_bash_deny_requires_backend_bound_trust(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_tool import _active_environments, _env_lock

        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        try:
            command = "curl https://example.com"
            settings_path = f"{project}/.claude/settings.local.json"
            write = env.execute(
                f"cat > {shlex.quote(settings_path)}", cwd=project,
                stdin_data=json.dumps({"permissions": {"deny": [f"Bash({command})"]}}), timeout=20,
            )
            self.assertEqual(write["returncode"], 0, write)
            with TemporaryDirectory(prefix="remote-project-policy-") as directory:
                root = Path(directory)
                user_settings = root / "settings.json"
                user_settings.write_text(json.dumps({
                    "hooks": {}, "permissions": {"allow": [f"Bash({command})"]},
                }))
                trust = root / "remote-projects.json"
                trust.write_text('{"projects":[]}')
                with patch.dict(os.environ, {"LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}):
                    bridge = HookBridge(user_settings, root)
                try:
                    self.assertIsNone(bridge.command_approval(
                        command, session_key="remote-permission", cwd=project, task_id="default",
                    ))
                    trust.write_text(json.dumps({"projects": [{
                        "type": "ssh", "host": host, "user": user, "port": 22, "root": project,
                    }]}))
                    self.assertEqual(bridge.command_approval(
                        command, session_key="remote-permission", cwd=project, task_id="default",
                    ), {"action": "deny"})
                finally:
                    bridge.close()
        finally:
            env.execute(f"rm -f {shlex.quote(settings_path)}", cwd=project, timeout=20)
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)

    def test_ssh_project_hook_requires_backend_bound_trust(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_tool import _active_environments, _env_lock

        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        try:
            reset = env.execute("rm -f .claude/settings.local.json", cwd=project, timeout=20)
            self.assertEqual(reset["returncode"], 0, reset["output"])
            code = (
                "import json,sys; data=json.load(sys.stdin); "
                "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
                "'permissionDecision':'deny','permissionDecisionReason':'remote project guard'}}))"
            )
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command", "command": "python3 -c " + shlex.quote(code),
            }]}]}}
            write = env.execute("cat > .claude/settings.json", cwd=project,
                                stdin_data=json.dumps(settings), timeout=20)
            self.assertEqual(write["returncode"], 0, write["output"])

            with TemporaryDirectory(prefix="remote-project-hook-") as directory:
                root = Path(directory)
                user_settings = root / "settings.json"
                user_settings.write_text('{"hooks":{}}')
                trust = root / "remote-projects.json"
                trust.write_text('{"projects":[]}')
                with patch.dict(os.environ, {"LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}):
                    bridge = HookBridge(user_settings, root)
                try:
                    args = {"command": "printf ready", "workdir": project}
                    self.assertIsNone(bridge.pre_tool_call(
                        "terminal", args, session_id="remote-project-test", task_id="default",
                    ))
                    trust.write_text(json.dumps({"projects": [{
                        "type": "ssh", "host": "wrong-host", "user": user,
                        "port": 22, "root": project,
                    }]}))
                    self.assertIsNone(bridge.pre_tool_call(
                        "terminal", args, session_id="remote-project-test", task_id="default",
                    ))
                    trust.write_text(json.dumps({"projects": [{
                        "type": "ssh", "host": host, "user": user,
                        "port": 22, "root": project,
                    }]}))
                    trust.chmod(0o666)
                    self.assertIsNone(bridge.pre_tool_call(
                        "terminal", args, session_id="remote-project-test", task_id="default",
                    ))
                    trust.chmod(0o600)
                    verdict = bridge.pre_tool_call(
                        "terminal", args, session_id="remote-project-test", task_id="default",
                    )
                    self.assertEqual(verdict, {"action": "block", "message": "remote project guard"})
                    outside = f"/home/{user}/outside"
                    link = f"{project}/linked-outside"
                    setup = env.execute(
                        f"mkdir -p {shlex.quote(outside)} && ln -sfn {shlex.quote(outside)} {shlex.quote(link)}",
                        cwd=project, timeout=20,
                    )
                    self.assertEqual(setup["returncode"], 0, setup["output"])
                    escaped = bridge.pre_tool_call(
                        "terminal", {"command": "printf ready", "workdir": link},
                        session_id="remote-project-test", task_id="default",
                    )
                    self.assertIsNone(escaped)
                    empty = env.execute("cat > .claude/settings.json", cwd=project,
                                        stdin_data='{"hooks":{}}', timeout=20)
                    self.assertEqual(empty["returncode"], 0, empty["output"])
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        cleared = bridge.pre_tool_call(
                            "terminal", args, session_id="remote-project-test", task_id="default",
                        )
                        if cleared is None:
                            break
                        time.sleep(0.05)
                    self.assertIsNone(cleared)
                    local_settings = env.execute("cat > .claude/settings.local.json", cwd=project,
                                                 stdin_data=json.dumps(settings), timeout=20)
                    self.assertEqual(local_settings["returncode"], 0, local_settings["output"])
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        local_verdict = bridge.pre_tool_call(
                            "terminal", args, session_id="remote-project-test", task_id="default",
                        )
                        if local_verdict is not None:
                            break
                        time.sleep(0.05)
                    self.assertEqual(local_verdict, {"action": "block", "message": "remote project guard"})
                finally:
                    bridge.close()
        finally:
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup()

    def test_async_ssh_project_hook_survives_parent_exit(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment

        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        try:
            code = (
                "import json,sys,time; json.load(sys.stdin); time.sleep(0.2); "
                "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
                "'additionalContext':'REMOTE_ASYNC_READY'}}))"
            )
            remote_settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command", "command": "python3 -c " + shlex.quote(code), "async": True,
            }]}]}}
            for name, content in (("settings.json", remote_settings), ("settings.local.json", {"hooks": {}})):
                write = env.execute(f"cat > .claude/{name}", cwd=project,
                                    stdin_data=json.dumps(content), timeout=20)
                self.assertEqual(write["returncode"], 0, write["output"])

            with TemporaryDirectory(prefix="remote-async-project-") as directory:
                root = Path(directory)
                user_settings = root / "settings.json"
                user_settings.write_text('{"hooks":{}}')
                trust = root / "remote-projects.json"
                trust.write_text(json.dumps({"projects": [{
                    "type": "ssh", "host": host, "user": user, "port": 22, "root": project,
                }]}))
                session = "remote-async-project-test"
                driver = (
                    "import os\nfrom pathlib import Path\n"
                    "from tools.environments.ssh import SSHEnvironment\n"
                    "from tools.terminal_tool import _active_environments,_env_lock\n"
                    "from lifeos_hook_bridge.bridge import HookBridge\n"
                    f"env=SSHEnvironment(host={host!r},user={user!r},cwd={project!r},"
                    f"key_path={key!r},probe_only=True)\n"
                    "with _env_lock: _active_environments['default']=env\n"
                    f"bridge=HookBridge(Path({str(user_settings)!r}),Path({str(root)!r}))\n"
                    f"bridge.pre_tool_call('terminal',{{'command':'printf ready','workdir':{project!r}}},"
                    f"session_id={session!r},task_id='default')\n"
                    "os._exit(0)\n"
                )
                child_env = {**os.environ, "LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}
                child = subprocess.run([sys.executable, "-c", driver], cwd=Path(__file__).resolve().parents[1],
                                       env=child_env, capture_output=True, text=True, timeout=20)
                self.assertEqual(child.returncode, 0, child.stderr)
                bridge = HookBridge(user_settings, root)
                try:
                    result_dir = bridge._async_result_dir(session)
                    deadline = time.monotonic() + 10
                    while not list(result_dir.glob("*.json")) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertTrue(list(result_dir.glob("*.json")))
                    next_turn = bridge.pre_llm_call("second", session_id=session)
                    self.assertIn("REMOTE_ASYNC_READY", next_turn["context"])
                finally:
                    bridge.close()
        finally:
            env.cleanup()

    def test_remote_settings_change_reaches_config_change_hooks(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_tool import _active_environments, _env_lock

        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        try:
            with TemporaryDirectory(prefix="remote-config-change-") as directory:
                root = Path(directory)
                marker = root / "config-change.json"
                recorder = root / "record.py"
                recorder.write_text(
                    "import json,sys\nfrom pathlib import Path\n"
                    f"Path({str(marker)!r}).write_text(json.dumps(json.load(sys.stdin)))\n"
                )
                user_settings = root / "settings.json"
                user_settings.write_text(json.dumps({"hooks": {"ConfigChange": [{"hooks": [{
                    "type": "command", "command": f"{sys.executable} {recorder}",
                }]}]}}))
                trust = root / "remote-projects.json"
                trust.write_text(json.dumps({"projects": [{
                    "type": "ssh", "host": host, "user": user, "port": 22, "root": project,
                }]}))
                remote_marker = f"{project}/config-change.marker"
                env.execute(f"rm -f {shlex.quote(remote_marker)}", cwd=project, timeout=20)
                remote_code = f"from pathlib import Path; Path({remote_marker!r}).write_text('done')"
                remote_settings = {"hooks": {"ConfigChange": [{"hooks": [{
                    "type": "command", "command": "python3 -c " + shlex.quote(remote_code),
                }]}]}}
                reset = env.execute("cat > .claude/settings.json", cwd=project,
                                    stdin_data=json.dumps(remote_settings), timeout=20)
                self.assertEqual(reset["returncode"], 0, reset["output"])
                skill_path = f"{project}/.claude/skills/probe/SKILL.md"
                baseline_skill = env.execute(
                    "mkdir -p .claude/skills/probe && cat > .claude/skills/probe/SKILL.md",
                    cwd=project, stdin_data="first version", timeout=20,
                )
                self.assertEqual(baseline_skill["returncode"], 0, baseline_skill["output"])
                with patch.dict(os.environ, {"LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}):
                    bridge = HookBridge(user_settings, root)
                try:
                    session = "remote-config-session"
                    bridge.pre_llm_call("start", session_id=session)
                    bridge.pre_tool_call("terminal", {"command": "true", "workdir": project},
                                         session_id=session, task_id="default")
                    remote_settings["env"] = {"LIFEOS_CONFIG_PROBE": "changed"}
                    edit = env.execute("cat > .claude/settings.json", cwd=project,
                                       stdin_data=json.dumps(remote_settings), timeout=20)
                    self.assertEqual(edit["returncode"], 0, edit["output"])
                    deadline = time.monotonic() + 6
                    while not marker.exists() and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertTrue(marker.exists())
                    event = json.loads(marker.read_text())
                    self.assertEqual(event["source"], "project_settings")
                    self.assertEqual(event["file_path"], f"{project}/.claude/settings.json")
                    remote_result = env.execute(f"cat {shlex.quote(remote_marker)}", cwd=project, timeout=20)
                    self.assertEqual(remote_result["output"].strip(), "done")
                    marker.unlink()
                    changed_skill = env.execute("cat > .claude/skills/probe/SKILL.md", cwd=project,
                                                stdin_data="second version", timeout=20)
                    self.assertEqual(changed_skill["returncode"], 0, changed_skill["output"])
                    deadline = time.monotonic() + 6
                    while not marker.exists() and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertTrue(marker.exists())
                    skill_event = json.loads(marker.read_text())
                    self.assertEqual(skill_event["source"], "skills")
                    self.assertEqual(skill_event["file_path"], skill_path)
                finally:
                    bridge.close()
        finally:
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup()

    def test_remote_project_http_hook_uses_backend_loopback(self):
        host = os.environ.get("LIFEOS_SSH_PROBE_HOST")
        user = os.environ.get("LIFEOS_SSH_PROBE_USER")
        key = os.environ.get("LIFEOS_SSH_PROBE_KEY")
        project = os.environ.get("LIFEOS_SSH_PROBE_PROJECT")
        if not all((host, user, key, project)):
            self.skipTest("disposable SSH project is required")

        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_tool import _active_environments, _env_lock

        seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                data = json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": "remote HTTP guard",
                }}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = SSHEnvironment(host=host, user=user, cwd=project, key_path=key, probe_only=True)
        with _env_lock:
            _active_environments["default"] = env
        try:
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "http", "url": f"http://127.0.0.1:{server.server_port}/hook",
            }]}]}}
            for name, content in (("settings.json", settings), ("settings.local.json", {"hooks": {}})):
                written = env.execute(f"cat > .claude/{name}", cwd=project,
                                      stdin_data=json.dumps(content), timeout=20)
                self.assertEqual(written["returncode"], 0, written["output"])
            with TemporaryDirectory(prefix="remote-http-project-") as directory:
                root = Path(directory)
                user_settings = root / "settings.json"
                user_settings.write_text('{"hooks":{}}')
                trust = root / "remote-projects.json"
                trust.write_text(json.dumps({"projects": [{
                    "type": "ssh", "host": host, "user": user, "port": 22, "root": project,
                }]}))
                with patch.dict(os.environ, {"LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}):
                    bridge = HookBridge(user_settings, root)
                try:
                    with patch.object(bridge, "_run_http", side_effect=AssertionError("host HTTP path used")):
                        verdict = bridge.pre_tool_call("terminal", {"command": "true", "workdir": project},
                                                       session_id="remote-http-session", task_id="default")
                    self.assertEqual(verdict, {"action": "block", "message": "remote HTTP guard"})
                    self.assertEqual(seen[0]["tool_name"], "Bash")
                finally:
                    bridge.close()
        finally:
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup()
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
