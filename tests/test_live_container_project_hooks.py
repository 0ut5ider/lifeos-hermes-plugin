# ABOUTME: Checks trusted project hook execution in a disposable Docker container.
# ABOUTME: Requires an explicit local image and temporary Docker socket access.

import json
import os
import shlex
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


class LiveContainerProjectHookTests(unittest.TestCase):
    def test_async_container_hook_survives_parent_exit(self):
        image = os.environ.get("LIFEOS_DOCKER_PROBE_IMAGE")
        if not image:
            self.skipTest("disposable Docker project is required")

        with TemporaryDirectory(prefix="container-async-parent-") as directory:
            root = Path(directory)
            user_settings = root / "settings.json"
            user_settings.write_text('{"hooks":{}}')
            trust = root / "remote-projects.json"
            container_record = root / "container-id"
            project = "/tmp/lifeos-async-parent-exit"
            session = "container-async-parent-test"
            code = (
                "import json,sys,time; json.load(sys.stdin); time.sleep(0.2); "
                "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
                "'additionalContext':'CONTAINER_PARENT_EXIT_READY'}}))"
            )
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command", "command": "python3 -c " + shlex.quote(code), "async": True,
            }]}]}}
            driver = "\n".join([
                "import json,os,subprocess",
                "from pathlib import Path",
                "from tools.environments.docker import DockerEnvironment",
                "from tools.terminal_tool import _active_environments,_env_lock",
                "from lifeos_hook_bridge.bridge import HookBridge",
                f"env=DockerEnvironment(image={image!r},cwd={project!r},"
                "task_id='lifeos-async-parent-probe',network=False,persistent_filesystem=False)",
                f"Path({str(container_record)!r}).write_text(env._container_id)",
                "image_id=subprocess.run([env._docker_exe,'inspect','--format','{{.Image}}',"
                "env._container_id],capture_output=True,text=True,check=True,timeout=20).stdout.strip()",
                f"Path({str(trust)!r}).write_text(json.dumps({{'projects':[{{'type':'docker',"
                f"'image_id':image_id,'root':{project!r}}}]}}))",
                f"written=env.execute('mkdir -p .claude && cat > .claude/settings.json',"
                f"cwd={project!r},stdin_data={json.dumps(settings)!r},timeout=20)",
                "assert written['returncode']==0,written",
                "with _env_lock: _active_environments['default']=env",
                f"bridge=HookBridge(Path({str(user_settings)!r}),Path({str(root)!r}))",
                f"bridge.pre_tool_call('terminal',{{'command':'true','workdir':{project!r}}},"
                f"session_id={session!r},task_id='default')",
                "os._exit(0)",
            ])
            child_env = {**os.environ, "LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}
            container_id = None
            try:
                child = subprocess.run(
                    [sys.executable, "-c", driver], cwd=Path(__file__).resolve().parents[1],
                    env=child_env, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(child.returncode, 0, child.stderr[-1500:])
                container_id = container_record.read_text().strip()
                bridge = HookBridge(user_settings, root)
                try:
                    result_dir = bridge._async_result_dir(session)
                    deadline = time.monotonic() + 10
                    while not list(result_dir.glob("*.json")) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertTrue(list(result_dir.glob("*.json")))
                    next_turn = bridge.pre_llm_call("second", session_id=session)
                    self.assertIn("CONTAINER_PARENT_EXIT_READY", next_turn["context"])
                finally:
                    bridge.close()
            finally:
                if container_id:
                    subprocess.run(["docker", "rm", "-f", container_id],
                                   capture_output=True, text=True, check=False, timeout=20)

    def test_container_project_hook_requires_image_bound_trust(self):
        image = os.environ.get("LIFEOS_DOCKER_PROBE_IMAGE")
        if not image:
            self.skipTest("disposable Docker project is required")

        from tools.environments.docker import DockerEnvironment
        from tools.file_tools import clear_file_ops_cache
        from tools.terminal_tool import _active_environments, _env_lock

        project = "/tmp/lifeos-project-hook-probe"
        env = DockerEnvironment(image=image, cwd=project, task_id="lifeos-project-hook-probe",
                                network=False, persistent_filesystem=False)
        with _env_lock:
            _active_environments["default"] = env
        try:
            code = (
                "import json,sys; json.load(sys.stdin); "
                "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
                "'permissionDecision':'deny','permissionDecisionReason':'container project guard'}}))"
            )
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command", "command": "python3 -c " + shlex.quote(code),
            }]}]}}
            marker = f"{project}/config-change.marker"
            recorder = (
                "import json,sys; from pathlib import Path; "
                f"Path({marker!r}).write_text(json.load(sys.stdin)['source'])"
            )
            settings["hooks"]["ConfigChange"] = [{"hooks": [{
                "type": "command", "command": "python3 -c " + shlex.quote(recorder),
            }]}]
            env.execute(f"rm -f {shlex.quote(marker)} && mkdir -p .claude/skills/probe",
                        cwd=project, timeout=20)
            env.execute("cat > .claude/skills/probe/SKILL.md", cwd=project,
                        stdin_data="first version", timeout=20)
            write = env.execute("mkdir -p .claude && cat > .claude/settings.json", cwd=project,
                                stdin_data=json.dumps(settings), timeout=20)
            self.assertEqual(write["returncode"], 0, write["output"])
            inspect = subprocess.run(
                [env._docker_exe, "inspect", "--format", "{{.Image}}", env._container_id],
                capture_output=True, text=True, check=True, timeout=20,
            )
            image_id = inspect.stdout.strip()
            with TemporaryDirectory(prefix="container-project-hook-") as directory:
                root = Path(directory)
                user_settings = root / "settings.json"
                user_settings.write_text('{"hooks":{}}')
                trust = root / "remote-projects.json"
                trust.write_text('{"projects":[]}')
                with patch.dict(os.environ, {"LIFEOS_REMOTE_PROJECT_TRUST": str(trust)}):
                    bridge = HookBridge(user_settings, root)
                try:
                    args = {"command": "printf ready", "workdir": project}
                    self.assertIsNone(bridge.pre_tool_call("terminal", args,
                                      session_id="container-project-test", task_id="default"))
                    trust.write_text(json.dumps({"projects": [{
                        "type": "docker", "image_id": "sha256:" + "0" * 64, "root": project,
                    }]}))
                    self.assertIsNone(bridge.pre_tool_call("terminal", args,
                                      session_id="container-project-test", task_id="default"))
                    trust.write_text(json.dumps({"projects": [{
                        "type": "docker", "image_id": image_id, "root": project,
                    }]}))
                    verdict = bridge.pre_tool_call("terminal", args,
                                                   session_id="container-project-test", task_id="default")
                    self.assertEqual(verdict, {"action": "block", "message": "container project guard"})
                    escaped = env.execute("mkdir -p /tmp/lifeos-outside && ln -sfn /tmp/lifeos-outside escape",
                                          cwd=project, timeout=20)
                    self.assertEqual(escaped["returncode"], 0, escaped["output"])
                    self.assertIsNone(bridge.pre_tool_call(
                        "terminal", {"command": "true", "workdir": f"{project}/escape"},
                        session_id="container-project-test", task_id="default",
                    ))
                    bridge.pre_llm_call("start", session_id="container-project-test")
                    settings["env"] = {"LIFEOS_CONFIG_PROBE": "changed"}
                    edit = env.execute("cat > .claude/settings.json", cwd=project,
                                       stdin_data=json.dumps(settings), timeout=20)
                    self.assertEqual(edit["returncode"], 0, edit["output"])
                    bridge.poll_remote_config_changes()
                    changed = env.execute("cat config-change.marker", cwd=project, timeout=20)
                    self.assertEqual(changed["output"].strip(), "project_settings")
                    env.execute("rm -f config-change.marker", cwd=project, timeout=20)
                    skill = env.execute("cat > .claude/skills/probe/SKILL.md", cwd=project,
                                        stdin_data="second version", timeout=20)
                    self.assertEqual(skill["returncode"], 0, skill["output"])
                    bridge.poll_remote_config_changes()
                    changed = env.execute("cat config-change.marker", cwd=project, timeout=20)
                    self.assertEqual(changed["output"].strip(), "skills")

                    async_code = (
                        "import json,sys,time; json.load(sys.stdin); time.sleep(0.2); "
                        "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
                        "'additionalContext':'CONTAINER_ASYNC_READY'}}))"
                    )
                    settings["hooks"]["PreToolUse"] = [{"matcher": "Bash", "hooks": [{
                        "type": "command", "command": "python3 -c " + shlex.quote(async_code),
                        "async": True,
                    }]}]
                    edit = env.execute("cat > .claude/settings.json", cwd=project,
                                       stdin_data=json.dumps(settings), timeout=20)
                    self.assertEqual(edit["returncode"], 0, edit["output"])
                    bridge.poll_remote_config_changes()
                    self.assertIsNone(bridge.pre_tool_call("terminal", args,
                                      session_id="container-project-test", task_id="default"))
                    result_dir = bridge._async_result_dir("container-project-test")
                    deadline = time.monotonic() + 10
                    while not list(result_dir.glob("*.json")) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertTrue(list(result_dir.glob("*.json")))
                    next_turn = bridge.pre_llm_call("second", session_id="container-project-test")
                    self.assertIn("CONTAINER_ASYNC_READY", next_turn["context"])

                    server_code = (
                        "import json\nfrom pathlib import Path\n"
                        "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
                        "class Handler(BaseHTTPRequestHandler):\n"
                        " def do_POST(self):\n"
                        "  body=self.rfile.read(int(self.headers['Content-Length']))\n"
                        "  Path('request.json').write_bytes(body)\n"
                        "  response=json.dumps({'hookSpecificOutput':{"
                        "'hookEventName':'PreToolUse','permissionDecision':'deny',"
                        "'permissionDecisionReason':'container HTTP guard'}}).encode()\n"
                        "  self.send_response(200)\n"
                        "  self.send_header('Content-Length',str(len(response)))\n"
                        "  self.end_headers()\n"
                        "  self.wfile.write(response)\n"
                        " def log_message(self,*args): pass\n"
                        "HTTPServer(('127.0.0.1',45678),Handler).serve_forever()\n"
                    )
                    write_server = env.execute("cat > server.py", cwd=project,
                                               stdin_data=server_code, timeout=20)
                    self.assertEqual(write_server["returncode"], 0, write_server["output"])
                    server = subprocess.run(
                        [env._docker_exe, "exec", "-d", "--workdir", project,
                         env._container_id, "python3", "server.py"],
                        capture_output=True, text=True, check=False, timeout=20,
                    )
                    self.assertEqual(server.returncode, 0, server.stderr)
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        ready = env.execute(
                            "curl --noproxy '*' --silent --output /dev/null http://127.0.0.1:45678/",
                            cwd=project, timeout=5,
                        )
                        if ready["returncode"] == 0:
                            break
                        time.sleep(0.05)
                    self.assertEqual(ready["returncode"], 0, ready["output"])
                    settings["hooks"]["PreToolUse"] = [{"matcher": "Bash", "hooks": [{
                        "type": "http", "url": "http://127.0.0.1:45678/hook",
                    }]}]
                    edit = env.execute("cat > .claude/settings.json", cwd=project,
                                       stdin_data=json.dumps(settings), timeout=20)
                    self.assertEqual(edit["returncode"], 0, edit["output"])
                    bridge.poll_remote_config_changes()
                    with patch.object(bridge, "_run_http", side_effect=AssertionError("host HTTP path used")):
                        verdict = bridge.pre_tool_call("terminal", args,
                                                       session_id="container-project-test", task_id="default")
                    self.assertEqual(verdict, {"action": "block", "message": "container HTTP guard"})
                    received = env.execute("cat request.json", cwd=project, timeout=20)
                    self.assertEqual(json.loads(received["output"])["tool_name"], "Bash")
                    env.execute("rm -f config-change.marker", cwd=project, timeout=20)
                    trust.write_text('{"projects":[]}')
                    edit = env.execute("cat > .claude/skills/probe/SKILL.md", cwd=project,
                                       stdin_data="trust revoked", timeout=20)
                    self.assertEqual(edit["returncode"], 0, edit["output"])
                    bridge.poll_remote_config_changes()
                    marker_after_revoke = env.execute("test -e config-change.marker", cwd=project, timeout=20)
                    self.assertNotEqual(marker_after_revoke["returncode"], 0)
                finally:
                    bridge.close()
        finally:
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup(force_remove=True)
            self.assertTrue(env.wait_for_cleanup(timeout=30))
