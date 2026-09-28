# ABOUTME: Tests native LifeOS hook execution through the Hermes event bridge.
# ABOUTME: Uses real child processes and Claude hook JSON contracts.

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


class HookBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hooks = self.root / "hooks"
        self.hooks.mkdir()

    def make_hook(self, name, body):
        path = self.hooks / name
        path.write_text(body)
        return f"{sys.executable} {path}"

    def bridge(self, hooks):
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"hooks": hooks}))
        bridge = HookBridge(settings, self.root)
        self.addCleanup(bridge.close)
        return bridge

    def test_pre_tool_block_uses_claude_payload_and_exit_code(self):
        command = self.make_hook(
            "deny.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['hook_event_name']=='PreToolUse'\n"
            "assert data['tool_name']=='Bash'\n"
            "assert data['tool_input']['command']=='echo hi'\n"
            "print('blocked by test',file=sys.stderr)\n"
            "sys.exit(2)\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]})
        result = bridge.pre_tool_call("terminal", {"command": "echo hi"}, session_id="s1")
        self.assertEqual(result, {"action": "block", "message": "blocked by test"})

    def test_terminal_hook_uses_tool_workdir(self):
        workdir = self.root / "tool-workspace"
        workdir.mkdir()
        marker = workdir / "observed-cwd"
        command = self.make_hook(
            "record-cwd.py",
            "import json,os,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            "assert data['cwd']==os.getcwd()\n"
            f"Path({str(marker)!r}).write_text(data['cwd'])\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]})
        bridge.pre_tool_call("terminal", {"command": "pwd", "workdir": str(workdir)}, session_id="s1")
        self.assertEqual(marker.read_text(), str(workdir))

    def test_project_hook_applies_only_to_its_project(self):
        project = self.root / "project-a"
        other = self.root / "project-b"
        (project / ".claude").mkdir(parents=True)
        other.mkdir()
        deny = self.make_hook("project-deny.py", "import sys\nprint('project denied', file=sys.stderr)\nsys.exit(2)\n")
        (project / ".claude/settings.json").write_text(json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": deny}]}],
        }}))
        bridge = self.bridge({})
        with patch("lifeos_hook_bridge.bridge._trusted_project", side_effect=lambda path: path == project):
            result = bridge.pre_tool_call(
                "terminal", {"command": "pwd", "workdir": str(project)}, session_id="project-a-session",
            )
        self.assertEqual(result, {"action": "block", "message": "project denied"})
        result = bridge.pre_tool_call(
            "terminal", {"command": "pwd", "workdir": str(other)}, session_id="project-b-session",
        )
        self.assertIsNone(result)

    def test_project_hook_reloads_after_settings_change(self):
        project = self.root / "project-a"
        settings_dir = project / ".claude"
        settings_dir.mkdir(parents=True)
        settings = settings_dir / "settings.json"
        settings.write_text(json.dumps({"hooks": {}}))
        deny = self.make_hook("project-deny.py", "import sys\nprint('reloaded deny', file=sys.stderr)\nsys.exit(2)\n")
        bridge = self.bridge({})
        args = {"command": "pwd", "workdir": str(project)}
        self.assertIsNone(bridge.pre_tool_call("terminal", args, session_id="s1"))
        settings.write_text(json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": deny}]}],
        }}))
        bridge.poll_config_changes(force=True)
        with patch("lifeos_hook_bridge.bridge._trusted_project", return_value=True):
            result = bridge.pre_tool_call("terminal", args, session_id="s1")
        self.assertEqual(result, {"action": "block", "message": "reloaded deny"})

    def test_nested_workdir_finds_trusted_repository_hooks(self):
        project = self.root / "repository"
        nested = project / "src" / "nested"
        (project / ".git").mkdir(parents=True)
        (project / ".claude").mkdir()
        nested.mkdir(parents=True)
        deny = self.make_hook("root-deny.py", "import sys\nprint('root hook', file=sys.stderr)\nsys.exit(2)\n")
        (project / ".claude/settings.json").write_text(json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": deny}]}],
        }}))
        bridge = self.bridge({})
        with patch("lifeos_hook_bridge.bridge._trusted_project", side_effect=lambda path: path == project):
            result = bridge.pre_tool_call(
                "terminal", {"command": "pwd", "workdir": str(nested)}, session_id="s1",
            )
        self.assertEqual(result, {"action": "block", "message": "root hook"})

    def test_one_session_uses_hooks_for_each_repository_workdir(self):
        projects = []
        for label in ("alpha", "beta"):
            project = self.root / label
            (project / ".git").mkdir(parents=True)
            (project / ".claude").mkdir()
            nested = project / "src"
            nested.mkdir()
            command = self.make_hook(
                f"{label}.py", f"import sys\nprint({label!r}, file=sys.stderr)\nsys.exit(2)\n",
            )
            (project / ".claude/settings.json").write_text(json.dumps({"hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}],
            }}))
            projects.append((project, nested, label))
        bridge = self.bridge({})
        with patch("lifeos_hook_bridge.bridge._trusted_project", return_value=True):
            for _, nested, label in projects:
                result = bridge.pre_tool_call(
                    "terminal", {"command": "pwd", "workdir": str(nested)}, session_id="shared-session",
                )
                self.assertEqual(result, {"action": "block", "message": label})

    def test_untrusted_project_hook_does_not_execute(self):
        project = self.root / "untrusted"
        (project / ".claude").mkdir(parents=True)
        marker = self.root / "ran"
        command = self.make_hook("unsafe.py", f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
        (project / ".claude/settings.json").write_text(json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}],
        }}))
        bridge = self.bridge({})
        with patch("lifeos_hook_bridge.bridge._trusted_project", return_value=False):
            bridge.pre_tool_call("terminal", {"command": "pwd", "workdir": str(project)}, session_id="s1")
        self.assertFalse(marker.exists())

    def test_trusted_project_environment_reaches_its_hook(self):
        project = self.root / "project-env"
        (project / ".claude").mkdir(parents=True)
        marker = self.root / "project-env-value"
        command = self.make_hook(
            "project-env.py",
            "import os\nfrom pathlib import Path\n"
            f"Path({str(marker)!r}).write_text(os.environ.get('LIFEOS_PROJECT_PROBE', 'missing'))\n",
        )
        (project / ".claude/settings.json").write_text(json.dumps({
            "env": {"LIFEOS_PROJECT_PROBE": "project-value"},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]},
        }))
        bridge = self.bridge({})
        with patch("lifeos_hook_bridge.bridge._trusted_project", return_value=True):
            bridge.pre_tool_call("terminal", {"command": "pwd", "workdir": str(project)}, session_id="s1")
        self.assertEqual(marker.read_text(), "project-value")
        other = self.root / "other-project"
        (other / ".claude").mkdir(parents=True)
        (other / ".claude/settings.json").write_text(json.dumps({
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]},
        }))
        with patch("lifeos_hook_bridge.bridge._trusted_project", return_value=True):
            bridge.pre_tool_call("terminal", {"command": "pwd", "workdir": str(other)}, session_id="s2")
        self.assertEqual(marker.read_text(), "missing")

    def test_blocked_pre_tool_hook_still_runs_later_observer(self):
        marker = self.root / "observer-ran"
        deny = self.make_hook("deny.py", "import sys\nprint('blocked',file=sys.stderr)\nsys.exit(2)\n")
        observe = self.make_hook("observe.py", f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n")
        bridge = self.bridge({"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": deny}, {"type": "command", "command": observe},
        ]}]})
        result = bridge.pre_tool_call("terminal", {"command": "echo test"}, session_id="s1")
        self.assertEqual(result["action"], "block")
        self.assertEqual(marker.read_text(), "ran")

    def test_matching_hooks_can_progress_concurrently(self):
        first_marker = self.root / "first-ready"
        second_marker = self.root / "second-ready"
        completed = self.root / "first-complete"
        first = self.make_hook(
            "first.py",
            "import time\nfrom pathlib import Path\n"
            f"Path({str(first_marker)!r}).touch()\n"
            f"other=Path({str(second_marker)!r})\n"
            "for _ in range(100):\n"
            " if other.exists(): break\n"
            " time.sleep(0.01)\n"
            "else: raise RuntimeError('second hook did not run concurrently')\n"
            f"Path({str(completed)!r}).touch()\n",
        )
        second = self.make_hook("second.py", f"from pathlib import Path\nPath({str(second_marker)!r}).touch()\n")
        bridge = self.bridge({"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": first}, {"type": "command", "command": second},
        ]}]})
        bridge.pre_llm_call("hello", session_id="s1")
        self.assertTrue(first_marker.exists())
        self.assertTrue(second_marker.exists())
        self.assertTrue(completed.exists())

    def test_session_end_handlers_run_in_registration_order(self):
        marker = self.root / "learning-ready"
        first = self.make_hook(
            "capture-learning.py",
            "import time\nfrom pathlib import Path\n"
            "time.sleep(0.2)\n"
            f"Path({str(marker)!r}).touch()\n",
        )
        second = self.make_hook(
            "cleanup-work.py",
            "import sys\nfrom pathlib import Path\n"
            f"sys.exit(0 if Path({str(marker)!r}).exists() else 2)\n",
        )
        bridge = self.bridge({"SessionEnd": [{"hooks": [
            {"type": "command", "command": first}, {"type": "command", "command": second},
        ]}]})
        outcomes = bridge._run("SessionEnd", bridge._payload("SessionEnd", "s1"))
        self.assertEqual([process.returncode for process, _ in outcomes], [0, 0])

    def test_async_hook_receives_complete_input_after_parent_exits(self):
        marker = self.root / "async-complete"
        command = self.make_hook(
            "async.py",
            "import json,sys,time\nfrom pathlib import Path\n"
            "time.sleep(0.2)\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(str(len(data['prompt'])))\n",
        )
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": command, "async": True},
        ]}]}}))
        driver = (
            "import os\nfrom pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n"
            f"bridge=HookBridge(Path({str(settings)!r}),Path({str(self.root)!r}))\n"
            "bridge.pre_llm_call('X'*1048576,session_id='s1')\n"
            "os._exit(0)\n"
        )
        process = subprocess.run([sys.executable, "-c", driver], cwd=Path(__file__).resolve().parents[1], timeout=10)
        self.assertEqual(process.returncode, 0)
        for _ in range(40):
            if marker.exists():
                break
            time.sleep(0.05)
        self.assertEqual(marker.read_text(), "1048576")

    def test_async_hook_context_reaches_next_turn_in_same_session(self):
        marker = self.root / "async-finished"
        command = self.make_hook(
            "async-context.py",
            "import json\nfrom pathlib import Path\n"
            "print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit',"
            " 'additionalContext': 'ASYNC_CONTEXT_READY'}, 'systemMessage': 'ASYNC_SYSTEM_READY'}), flush=True)\n"
            f"Path({str(marker)!r}).touch()\n",
        )
        bridge = self.bridge({"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": command, "async": True},
        ]}]})
        first = bridge.pre_llm_call("first", session_id="s1")
        self.assertFalse(first and "ASYNC_CONTEXT_READY" in first.get("context", ""))
        deadline = time.monotonic() + 4
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(marker.exists())
        time.sleep(0.15)
        other = bridge.pre_llm_call("other", session_id="s2")
        self.assertFalse(other and "ASYNC_CONTEXT_READY" in other.get("context", ""))
        second = bridge.pre_llm_call("second", session_id="s1")
        self.assertIn("ASYNC_CONTEXT_READY", second["context"])
        self.assertIn("ASYNC_SYSTEM_READY", second["context"])

    def test_async_hook_context_survives_parent_process_exit(self):
        command = self.make_hook(
            "async-persist.py",
            "import json\nprint(json.dumps({'hookSpecificOutput': "
            "{'hookEventName': 'UserPromptSubmit', 'additionalContext': 'PERSISTED_CONTEXT'}}))\n",
        )
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": command, "async": True},
        ]}]}}))
        driver = (
            "import os\nfrom pathlib import Path\n"
            "from lifeos_hook_bridge.bridge import HookBridge\n"
            f"bridge=HookBridge(Path({str(settings)!r}),Path({str(self.root)!r}))\n"
            "bridge.pre_llm_call('first',session_id='persistent-session')\n"
            "os._exit(0)\n"
        )
        process = subprocess.run(
            [sys.executable, "-c", driver], cwd=Path(__file__).resolve().parents[1], timeout=10,
        )
        self.assertEqual(process.returncode, 0)
        bridge = HookBridge(settings, self.root)
        self.addCleanup(bridge.close)
        result_dir = bridge._async_result_dir("persistent-session")
        deadline = time.monotonic() + 5
        while not list(result_dir.glob("*.json")) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(list(result_dir.glob("*.json")))
        bridge.hooks = {}
        next_turn = bridge.pre_llm_call("second", session_id="persistent-session")
        self.assertIn("PERSISTED_CONTEXT", next_turn["context"])

    def test_pre_tool_updated_input_maps_back_to_hermes(self):
        command = self.make_hook(
            "modify.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['tool_name']=='Bash'\n"
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','updatedInput':{'command':'echo safe'}}}))\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]})
        result = bridge.pre_tool_call("terminal", {"command": "echo original"}, session_id="s1")
        self.assertEqual(result, {"action": "modify", "args": {"command": "echo safe"}})

    def test_file_permission_grant_allows_a_write(self):
        marker = self.root / "grant-ran"
        command = self.make_hook(
            "file-permission.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['hook_event_name']=='PermissionRequest'\n"
            "assert data['tool_name']=='Write'\n"
            "assert data['tool_input']['file_path']=='/tmp/example.txt'\n"
            f"from pathlib import Path; Path({str(marker)!r}).touch()\n"
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'allow'}}}))\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Write", "hooks": [{"type": "command", "command": command}]}]})
        self.assertIsNone(bridge.pre_tool_call("write_file", {"path": "/tmp/example.txt", "content": "safe"}, session_id="s1"))
        self.assertTrue(marker.exists())

    def test_file_permission_neutral_requests_review(self):
        command = self.make_hook("neutral.py", "import json,sys\nassert json.load(sys.stdin)['tool_name']=='Edit'\n")
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Edit", "hooks": [{"type": "command", "command": command}]}]})
        verdict = bridge.pre_tool_call("patch", {"path": "/tmp/example.txt", "new_string": "change"}, session_id="s1")
        self.assertEqual(verdict["action"], "approve")
        self.assertIn("/tmp/example.txt", verdict["message"])

    def test_file_permission_defers_to_existing_hermes_ssh_guard(self):
        marker = self.root / "lifeos-permission-ran"
        command = self.make_hook(
            "neutral-ssh.py",
            "import json,sys\nfrom pathlib import Path\n"
            "assert json.load(sys.stdin)['tool_name']=='Write'\n"
            f"Path({str(marker)!r}).touch()\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Write", "hooks": [{"type": "command", "command": command}]}]})
        with patch("lifeos_hook_bridge.bridge._hermes_write_requires_approval", return_value=True) as guard:
            verdict = bridge.pre_tool_call(
                "write_file", {"path": str(self.root / ".ssh/config"), "content": "Host example"}, session_id="s1",
            )
        self.assertIsNone(verdict)
        self.assertTrue(marker.exists())
        guard.assert_called_once()

    def test_file_permission_deny_still_blocks_hermes_guarded_write(self):
        command = self.make_hook(
            "deny-ssh.py",
            "import json,sys\njson.load(sys.stdin)\n"
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'deny','reason':'LifeOS denial'}}}))\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Write", "hooks": [{"type": "command", "command": command}]}]})
        with patch("lifeos_hook_bridge.bridge._hermes_write_requires_approval", return_value=True):
            verdict = bridge.pre_tool_call("write_file", {"path": str(self.root / ".ssh/config")}, session_id="s1")
        self.assertEqual(verdict, {"action": "block", "message": "LifeOS denial"})

    def test_file_review_keeps_pre_tool_input_change(self):
        change = self.make_hook(
            "change-path.py",
            "import json,sys\n"
            "assert json.load(sys.stdin)['tool_name']=='Write'\n"
            "print(json.dumps({'hookSpecificOutput':{'updatedInput':{'file_path':'/tmp/reviewed.txt','content':'safe'}}}))\n",
        )
        neutral = self.make_hook(
            "review-path.py",
            "import json,sys\n"
            "assert json.load(sys.stdin)['tool_input']['file_path']=='/tmp/reviewed.txt'\n",
        )
        bridge = self.bridge({
            "PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": change}]}],
            "PermissionRequest": [{"matcher": "Write", "hooks": [{"type": "command", "command": neutral}]}],
        })
        verdict = bridge.pre_tool_call("write_file", {"path": "/tmp/original.txt", "content": "unsafe"}, session_id="s1")
        self.assertEqual(verdict["action"], "approve")
        self.assertEqual(verdict["args"], {"path": "/tmp/reviewed.txt", "content": "safe"})

    def test_file_permission_checks_every_v4a_target_before_review(self):
        marker = self.root / "permission-paths"
        command = self.make_hook(
            "record-permission.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(data['tool_input']['file_path']+'\\n')\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Edit", "hooks": [{"type": "command", "command": command}]}]})
        patch_text = "*** Begin Patch\n*** Update File: /tmp/first.txt\n+one\n*** Update File: /tmp/second.txt\n+two\n*** End Patch"
        verdict = bridge.pre_tool_call("patch", {"mode": "patch", "patch": patch_text}, session_id="s1")
        self.assertEqual(verdict["action"], "approve")
        self.assertEqual(set(marker.read_text().splitlines()), {"/tmp/first.txt", "/tmp/second.txt"})

    def test_file_permission_checks_delete_and_move_targets(self):
        marker = self.root / "all-patch-paths"
        command = self.make_hook(
            "record-target.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(data['tool_input']['file_path']+'\\n')\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Edit", "hooks": [{"type": "command", "command": command}]}]})
        patch_text = (
            "*** Begin Patch\n"
            "*** Delete File: /tmp/deleted.txt\n"
            "*** Update File: /tmp/old.txt\n"
            "*** Move to: /tmp/new.txt\n"
            "+changed\n"
            "*** End Patch"
        )
        verdict = bridge.pre_tool_call("patch", {"mode": "patch", "patch": patch_text}, session_id="s1")
        self.assertEqual(verdict["action"], "approve")
        self.assertEqual(set(marker.read_text().splitlines()), {
            "/tmp/deleted.txt", "/tmp/old.txt", "/tmp/new.txt",
        })

    def test_config_change_reports_project_and_local_settings(self):
        project = self.root / "project"
        project_claude = project / ".claude"
        project_claude.mkdir(parents=True)
        marker = self.root / "config-sources.jsonl"
        command = self.make_hook(
            "record-config.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        previous = Path.cwd()
        try:
            os.chdir(project)
            bridge = self.bridge({"ConfigChange": [{"hooks": [{"type": "command", "command": command}]}]})
            bridge.pre_llm_call("start", session_id="s1")
            (project_claude / "settings.json").write_text("{}")
            (project_claude / "settings.local.json").write_text("{}")
            bridge.poll_config_changes(force=True)
        finally:
            os.chdir(previous)
        rows = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual({row["source"] for row in rows}, {"project_settings", "local_settings"})

    def test_config_change_follows_later_project(self):
        first = self.root / "first-project"
        second = self.root / "second-project"
        first.mkdir()
        (second / ".claude").mkdir(parents=True)
        settings = second / ".claude" / "settings.local.json"
        settings.write_text("{}")
        marker = self.root / "later-project.jsonl"
        command = self.make_hook(
            "record-later-project.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        previous = Path.cwd()
        try:
            os.chdir(first)
            bridge = self.bridge({"ConfigChange": [{"hooks": [{"type": "command", "command": command}]}]})
            bridge.pre_llm_call("first", session_id="s1")
            os.chdir(second)
            bridge.pre_llm_call("second", session_id="s2")
            self.assertFalse(marker.exists())
            settings.write_text('{"changed":true}')
            bridge.poll_config_changes(force=True)
        finally:
            os.chdir(previous)
        rows = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual({row["file_path"] for row in rows}, {str(settings)})

    def test_config_change_reaches_only_project_session(self):
        first = self.root / "first-project"
        second = self.root / "second-project"
        (first / ".claude").mkdir(parents=True)
        (second / ".claude").mkdir(parents=True)
        marker = self.root / "project-sessions.jsonl"
        command = self.make_hook(
            "record-project-session.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        previous = Path.cwd()
        try:
            os.chdir(first)
            bridge = self.bridge({"ConfigChange": [{"hooks": [{"type": "command", "command": command}]}]})
            bridge.pre_llm_call("first", session_id="s1")
            os.chdir(second)
            bridge.pre_llm_call("second", session_id="s2")
            (first / ".claude" / "settings.json").write_text("{}")
            bridge.poll_config_changes(force=True)
        finally:
            os.chdir(previous)
        rows = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual([row["session_id"] for row in rows], ["s1"])

    def test_config_change_reports_managed_policy_files(self):
        policy = self.root / "managed-policy"
        dropins = policy / "managed-settings.d"
        dropins.mkdir(parents=True)
        marker = self.root / "policy-sources.jsonl"
        command = self.make_hook(
            "record-policy.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        with patch("lifeos_hook_bridge.bridge.POLICY_DIRECTORY", policy):
            bridge = self.bridge({"ConfigChange": [{"hooks": [{"type": "command", "command": command}]}]})
            bridge.pre_llm_call("start", session_id="s1")
            (policy / "managed-settings.json").write_text("{}")
            (dropins / "team.json").write_text("{}")
            bridge.poll_config_changes(force=True)
        rows = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["source"] for row in rows}, {"policy_settings"})

    def test_config_change_runs_while_session_is_idle(self):
        marker = self.root / "idle-config-change"
        command = self.make_hook(
            "record-idle-config.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(data['source'])\n",
        )
        bridge = self.bridge({"ConfigChange": [{"hooks": [{"type": "command", "command": command}]}]})
        bridge.pre_llm_call("start", session_id="s1")
        settings = json.loads(bridge.settings_path.read_text())
        settings["env"] = {"SYNTHETIC_IDLE_CHANGE": "yes"}
        bridge.settings_path.write_text(json.dumps(settings))
        for _ in range(60):
            if marker.exists():
                break
            time.sleep(0.05)
        self.assertEqual(marker.read_text(), "user_settings")

    def test_prompt_context_preserves_hook_order(self):
        first = self.make_hook("first.py", "print('first context')\n")
        second = self.make_hook("second.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'additionalContext':'second context'}}))\n")
        bridge = self.bridge({"UserPromptSubmit": [{"hooks": [{"type": "command", "command": first}, {"type": "command", "command": second}]}]})
        result = bridge.pre_llm_call("hello", session_id="s1")
        self.assertEqual(result, {"context": "first context\n\nsecond context"})

    def test_stop_block_is_returned_to_control_gate(self):
        command = self.make_hook(
            "stop.py",
            "import json,sys\n"
            "from pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            "assert data['last_assistant_message']=='unfinished'\n"
            "rows=[json.loads(line) for line in Path(data['transcript_path']).read_text().splitlines()]\n"
            "assert rows[-1]['type']=='assistant'\n"
            "assert rows[-1]['message']['content']=='unfinished'\n"
            "print(json.dumps({'decision':'block','reason':'Finish the evidence check'}))\n",
        )
        bridge = self.bridge({"Stop": [{"hooks": [{"type": "command", "command": command}]}]})
        result = bridge.stop("unfinished", session_id="s1")
        self.assertEqual(result, {"action": "continue", "message": "Finish the evidence check"})

    def test_session_context_is_injected_on_first_prompt(self):
        command = self.make_hook(
            "start.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            "assert data['hook_event_name']=='SessionStart'\n"
            "assert not Path(data['transcript_path']).exists()\n"
            "print('<session>loaded</session>')\n",
        )
        bridge = self.bridge({"SessionStart": [{"hooks": [{"type": "command", "command": command}]}]})
        self.assertEqual(bridge.pre_llm_call("first", session_id="s1"), {"context": "<session>loaded</session>"})
        self.assertIsNone(bridge.pre_llm_call("second", session_id="s1"))
        transcript = bridge.transcript_path("s1")
        rows = [json.loads(line) for line in transcript.read_text().splitlines()]
        self.assertEqual([row["message"]["content"] for row in rows], ["first", "second"])

    def test_multimodal_first_prompt_runs_start_and_prompt_hooks(self):
        marker = self.root / "multimodal-events.jsonl"
        command = self.make_hook(
            "record-prompt.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        bridge = self.bridge({
            "SessionStart": [{"hooks": [{"type": "command", "command": command}]}],
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": command}]}],
        })
        message = [
            {"type": "text", "text": "Describe this photo"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
        ]
        bridge.pre_llm_call(message, session_id="s1")
        events = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual([item["hook_event_name"] for item in events], ["SessionStart", "UserPromptSubmit"])
        self.assertEqual(events[1]["prompt"], "Describe this photo")

    def test_post_tool_failure_runs_failure_hook(self):
        marker = self.root / "failure.json"
        command = self.make_hook(
            "failure.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(json.dumps(data))\n",
        )
        bridge = self.bridge({"PostToolUseFailure": [{"hooks": [{"type": "command", "command": command}]}]})
        bridge.post_tool_call("terminal", {"command": "false"}, '{"error":"failed"}', session_id="s1", tool_call_id="tc1", status="error", error_message="failed")
        payload = json.loads(marker.read_text())
        self.assertEqual(payload["hook_event_name"], "PostToolUseFailure")
        self.assertEqual(payload["tool_name"], "Bash")
        self.assertEqual(payload["error"], "failed")
        rows = [json.loads(line) for line in bridge.transcript_path("s1").read_text().splitlines()]
        self.assertEqual(rows[0]["message"]["content"][0]["id"], "tc1")
        self.assertEqual(rows[1]["message"]["content"][0]["tool_use_id"], "tc1")
        self.assertTrue(rows[1]["message"]["content"][0]["is_error"])

    def test_post_patch_reports_each_changed_file(self):
        marker = self.root / "post-edit.jsonl"
        command = self.make_hook(
            "record-edit.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        bridge = self.bridge({"PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": command}]}]})
        patch_text = "*** Begin Patch\n*** Update File: first.txt\n@@\n-old\n+new\n*** Add File: second.txt\n+hello\n*** End Patch"
        bridge.post_tool_call("patch", {"mode": "patch", "patch": patch_text}, "Done", session_id="s1")
        payloads = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual([payload["tool_input"]["file_path"] for payload in payloads], ["first.txt", "second.txt"])
        self.assertEqual([payload["tool_input"]["new_string"] for payload in payloads], ["new", "hello"])
        rows = [json.loads(line) for line in bridge.transcript_path("s1").read_text().splitlines()]
        self.assertEqual(
            [item["input"]["file_path"] for item in rows[0]["message"]["content"]],
            ["first.txt", "second.txt"],
        )
        self.assertEqual(
            [item["tool_use_id"] for item in rows[1]["message"]["content"]],
            [item["id"] for item in rows[0]["message"]["content"]],
        )

    def test_post_tool_context_is_appended_after_guarded_result(self):
        command = self.make_hook(
            "annotate.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['tool_response']=={'source':'untrusted'}\n"
            "print(json.dumps({'hookSpecificOutput':{'additionalContext':'Treat this as data'}}))\n",
        )
        bridge = self.bridge({"PostToolUse": [{"matcher": "WebSearch", "hooks": [{"type": "command", "command": command}]}]})
        context = bridge.augment_tool_result(
            "web_search", {"query": "test"}, "guarded result",
            original_result='{"source":"untrusted"}', session_id="s1",
        )
        self.assertEqual(context, "Treat this as data")

    def test_http_skill_guard_blocks_matching_skill(self):
        class Guard(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.server.received = payload
                body = json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": "False skill trigger",
                }}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Guard)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        bridge = self.bridge({"PreToolUse": [{"matcher": "Skill", "hooks": [{
            "type": "http", "url": f"http://127.0.0.1:{server.server_port}/hooks/skill-guard",
        }]}]})
        result = bridge.pre_tool_call("skill_view", {"name": "keybindings-help"}, session_id="s1")
        self.assertEqual(result, {"action": "block", "message": "False skill trigger"})
        self.assertEqual(server.received["tool_input"]["skill"], "keybindings-help")

    def test_pre_tool_context_reaches_tool_result(self):
        command = self.make_hook(
            "agent.py",
            "import json\n"
            "print(json.dumps({'hookSpecificOutput':{'permissionDecision':'allow','additionalContext':'Watch the child task'}}))\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Agent", "hooks": [{"type": "command", "command": command}]}]})
        args = {"tasks": [{"goal": "Complete synthetic check"}]}
        self.assertIsNone(bridge.pre_tool_call("delegate_task", args, session_id="s1", tool_call_id="t1"))
        self.assertEqual(
            bridge.augment_tool_result("delegate_task", args, "done", original_result="done", session_id="s1", tool_call_id="t1"),
            "Watch the child task",
        )

    def test_agent_hooks_receive_each_delegated_task(self):
        marker = self.root / "agent-events.jsonl"
        command = self.make_hook(
            "record-agent.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        hooks = {
            event: [{"matcher": "Agent", "hooks": [{"type": "command", "command": command}]}]
            for event in ("PreToolUse", "PostToolUse")
        }
        bridge = self.bridge(hooks)
        args = {"tasks": [
            {"goal": "Inspect the first file", "context": "Read only", "model": "local-small"},
            {"goal": "Inspect the second file", "context": "Read only"},
        ]}
        bridge.pre_tool_call("delegate_task", args, session_id="s1")
        bridge.post_tool_call("delegate_task", args, "completed", session_id="s1")
        rows = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual([row["tool_input"]["prompt"] for row in rows], [
            "Inspect the first file\n\nRead only", "Inspect the second file\n\nRead only",
            "Inspect the first file\n\nRead only", "Inspect the second file\n\nRead only",
        ])
        self.assertEqual([row["tool_input"]["description"] for row in rows[:2]], [
            "Inspect the first file", "Inspect the second file",
        ])
        self.assertEqual(rows[0]["tool_input"]["model"], "local-small")

    def test_background_delegation_reaches_agent_hook(self):
        marker = self.root / "background-agent.json"
        command = self.make_hook(
            "record-background.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(json.dumps(data))\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Agent", "hooks": [{"type": "command", "command": command}]}]})
        bridge.pre_tool_call("delegate_task", {"goal": "Inspect a synthetic report", "background": True}, session_id="s1")
        payload = json.loads(marker.read_text())
        self.assertIs(payload["tool_input"]["run_in_background"], True)

    def test_background_agent_watchdog_instruction_uses_hermes_delivery(self):
        command = self.make_hook(
            "watchdog-context.py",
            "import json\n"
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
            "'additionalContext':'WATCHDOG: Start Monitor({ command: test })'}}))\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Agent", "hooks": [{"type": "command", "command": command}]}]})
        with patch.object(bridge, "_ensure_agent_watchdog", return_value=True) as ensure:
            bridge.pre_tool_call(
                "delegate_task", {"goal": "Inspect a synthetic report", "background": True},
                session_id="s1", tool_call_id="agent-1",
            )
        ensure.assert_called_once_with("s1")
        context = bridge.pending_tool_context[("s1", "agent-1")]
        self.assertIn("Hermes process notifications", context[0])
        self.assertNotIn("Monitor(", context[0])

    def test_watchdog_mirror_tracks_only_active_children_in_own_session(self):
        bridge = self.bridge({})
        bridge.watchdog_dir.mkdir(parents=True)
        starts, activity = bridge._watchdog_paths("s1")
        starts.write_text("{}")
        activity.touch()
        old = time.time() - 20
        os.utime(activity, (old, old))
        bridge.watchdog_processes["s1"] = "fake-process"
        bridge.watchdog_last_active["s1"] = time.monotonic()
        bridge._sync_agent_watchdogs([
            {"delegation_id": "child-1", "parent_session_id": "s1", "status": "running",
             "role": "worker", "seconds_since_progress": 2},
            {"delegation_id": "child-2", "parent_session_id": "s2", "status": "running",
             "role": "other", "seconds_since_progress": 1},
        ])
        self.assertEqual(json.loads(starts.read_text()), {"child-1": {"subagent_type": "worker"}})
        self.assertGreater(activity.stat().st_mtime, old)
        bridge._sync_agent_watchdogs([])
        self.assertEqual(json.loads(starts.read_text()), {})
        bridge.watchdog_processes.clear()

    def test_watchdog_mirror_does_not_invent_progress(self):
        bridge = self.bridge({})
        bridge.watchdog_dir.mkdir(parents=True)
        starts, activity = bridge._watchdog_paths("s1")
        starts.write_text("{}")
        activity.touch()
        old = time.time() - 20
        os.utime(activity, (old, old))
        bridge.watchdog_processes["s1"] = "fake-process"
        bridge.watchdog_last_active["s1"] = time.monotonic()
        bridge._sync_agent_watchdogs([
            {"delegation_id": "child-1", "parent_session_id": "s1", "status": "running"},
        ])
        self.assertLess(activity.stat().st_mtime, time.time() - 10)
        bridge.watchdog_processes.clear()

    def test_mcp_name_matches_native_safety_hook(self):
        command = self.make_hook(
            "mcp.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['tool_name']=='mcp__calendar__events'\n"
            "print(json.dumps({'hookSpecificOutput':{'additionalContext':'External content warning'}}))\n",
        )
        bridge = self.bridge({"PostToolUse": [{"matcher": "mcp__.*", "hooks": [{"type": "command", "command": command}]}]})
        self.assertEqual(
            bridge.augment_tool_result("mcp__calendar__events", {}, "result", original_result="result", session_id="s1"),
            "External content warning",
        )

    def test_todo_creation_uses_lifeos_task_governance_rules(self):
        bridge = self.bridge({"TaskCreated": [{"hooks": [{"type": "command", "command": "true"}]}]})
        short = {"todos": [{"id": "task-1", "content": "short", "status": "pending"}]}
        result = bridge.pre_tool_call("todo_list", short, session_id="s1")
        self.assertEqual(result["action"], "block")
        self.assertIn("at least 10 characters", result["message"])

        valid = {"todos": [{"id": "task-1", "content": "A meaningful task", "status": "pending"}]}
        self.assertIsNone(bridge.pre_tool_call("todo_list", valid, session_id="s1", tool_call_id="t1"))
        bridge.task_result("todo_list", valid, '{"ok":true}', session_id="s1", tool_call_id="t1", status="ok")
        self.assertIsNone(bridge.pre_tool_call("todo_list", valid, session_id="s1"))
        self.assertEqual(bridge.task_counts["s1"], 1)

        other = {"todos": [
            {"id": f"task-{number}", "content": f"Meaningful task {number}", "status": "pending"}
            for number in range(2, 51)
        ]}
        self.assertIsNone(bridge.pre_tool_call("todo_list", other, session_id="s1", tool_call_id="t2"))
        over_limit = {"todos": [{"id": "task-51", "content": "Meaningful task 51", "status": "pending"}]}
        self.assertIn("limit of 50", bridge.pre_tool_call("todo_list", over_limit, session_id="s1")["message"])

    def test_kanban_task_creation_uses_same_lifeos_limit(self):
        bridge = self.bridge({"TaskCreated": [{"hooks": [{"type": "command", "command": "true"}]}]})
        short = bridge.pre_tool_call("kanban_create", {"title": "short", "assignee": "worker"}, session_id="s1")
        self.assertEqual(short["action"], "block")
        valid = {"title": "Meaningful task title", "body": "Describe the work", "assignee": "worker"}
        for number in range(50):
            call_id = f"kanban-{number}"
            self.assertIsNone(bridge.pre_tool_call("kanban_create", valid, session_id="s1", tool_call_id=call_id))
            bridge.task_result("kanban_create", valid, '{"ok":true}', session_id="s1", tool_call_id=call_id, status="ok")
        self.assertIn("limit of 50", bridge.pre_tool_call("kanban_create", valid, session_id="s1")["message"])

    def test_failed_task_creation_releases_reserved_slot(self):
        bridge = self.bridge({"TaskCreated": [{"hooks": [{"type": "command", "command": "true"}]}]})
        valid = {"title": "Meaningful task title", "assignee": "worker"}
        self.assertIsNone(bridge.pre_tool_call("kanban_create", valid, session_id="s1", tool_call_id="failed"))
        bridge.task_result("kanban_create", valid, '{"error":"validation failed"}', session_id="s1", tool_call_id="failed", status="error")
        self.assertEqual(bridge.task_counts.get("s1", 0), 0)
        for number in range(50):
            self.assertIsNone(bridge.pre_tool_call("kanban_create", valid, session_id="s1", tool_call_id=f"pending-{number}"))
        self.assertIn("limit of 50", bridge.pre_tool_call("kanban_create", valid, session_id="s1", tool_call_id="extra")["message"])

    def test_task_count_survives_bridge_restart_until_session_end(self):
        hooks = {"TaskCreated": [{"hooks": [{"type": "command", "command": "true"}]}]}
        first = self.bridge(hooks)
        todos = [{"id": str(number), "content": f"Document task number {number}"} for number in range(50)]
        args = {"todos": todos}
        self.assertIsNone(first.pre_tool_call("todo_list", args, session_id="persisted", tool_call_id="first"))
        first.task_result("todo_list", args, '{"ok":true}', session_id="persisted", tool_call_id="first", status="ok")
        first.close()

        second = self.bridge(hooks)
        self.assertIsNone(second.pre_tool_call("todo_list", args, session_id="persisted", tool_call_id="repeat"))
        more = {"todos": todos + [{"id": "50", "content": "Document the final extra task"}]}
        self.assertIn(
            "limit of 50",
            second.pre_tool_call("todo_list", more, session_id="persisted", tool_call_id="extra")["message"],
        )
        second.session_end(session_id="persisted")
        third = self.bridge(hooks)
        self.assertIsNone(third.pre_tool_call(
            "todo_list", {"todos": [more["todos"][-1]]}, session_id="persisted", tool_call_id="new",
        ))

    def test_malformed_task_state_blocks_new_task(self):
        hooks = {"TaskCreated": [{"hooks": [{"type": "command", "command": "true"}]}]}
        bridge = self.bridge(hooks)
        bridge._task_state_path("damaged").write_text("not JSON")
        result = bridge.pre_tool_call(
            "todo_list", {"todos": [{"id": "first", "content": "Document the first task"}]},
            session_id="damaged", tool_call_id="first",
        )
        self.assertIn("limit of 50", result["message"])

    def test_native_task_hook_receives_session_count_and_controls_creation(self):
        marker = self.root / "native-task-counts"
        command = self.make_hook(
            "task-governance.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            "if data.get('hermes_bridge_probe'):\n"
            " print(json.dumps({'hermes_bridge_task_governance':1}))\n"
            " sys.exit(0)\n"
            f"with Path({str(marker)!r}).open('a') as out: out.write(f\"{{data['session_id']}}:{{data['hermes_task_count']}}:{{data['task_description']}}\\n\")\n"
            "if data['hermes_task_count'] >= 1:\n"
            " print('native count blocked',file=sys.stderr)\n"
            " sys.exit(2)\n",
        )
        bridge = self.bridge({"TaskCreated": [{"hooks": [{"type": "command", "command": command}]}]})
        first = {"title": "First meaningful task", "assignee": "worker"}
        second = {"title": "Second meaningful task", "assignee": "worker"}
        self.assertIsNone(bridge.pre_tool_call("kanban_create", first, session_id="s1", tool_call_id="a"))
        bridge.task_result("kanban_create", first, '{"ok":true}', session_id="s1", tool_call_id="a", status="ok")
        self.assertEqual(
            bridge.pre_tool_call("kanban_create", second, session_id="s1", tool_call_id="b"),
            {"action": "block", "message": "native count blocked"},
        )
        self.assertIsNone(bridge.pre_tool_call("kanban_create", second, session_id="s2", tool_call_id="c"))
        self.assertEqual(marker.read_text().splitlines(), [
            "s1:0:First meaningful task", "s1:1:Second meaningful task", "s2:0:Second meaningful task",
        ])

    def test_native_permission_grant_applies_to_command(self):
        command = self.make_hook(
            "permission.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['hook_event_name']=='PermissionRequest'\n"
            "assert data['tool_name']=='Bash'\n"
            "assert data['tool_input']['command']=='rm -rf /tmp/synthetic'\n"
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'allow'}}}))\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]})
        self.assertEqual(
            bridge.command_approval("rm -rf /tmp/synthetic", session_key="s1"),
            {"action": "allow"},
        )

    def test_native_permission_without_grant_defers_to_hermes(self):
        command = self.make_hook("abstain.py", "import sys\nsys.stdin.read()\n")
        bridge = self.bridge({"PermissionRequest": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]})
        self.assertIsNone(bridge.command_approval("sudo systemctl restart example.service", session_key="s1"))

    def test_mcp_permission_requests_review_for_secret_shaped_input(self):
        command = self.make_hook(
            "mcp_permission.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "assert data['hook_event_name']=='PermissionRequest'\n"
            "assert data['tool_name']=='mcp__example__send'\n"
            "if data['tool_input'].get('message')=='ordinary text':\n"
            " print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'allow'}}}))\n",
        )
        bridge = self.bridge({"PermissionRequest": [{"matcher": "mcp__.*", "hooks": [{"type": "command", "command": command}]}]})
        self.assertIsNone(bridge.pre_tool_call("mcp__example__send", {"message": "ordinary text"}, session_id="s1"))
        review = bridge.pre_tool_call("mcp__example__send", {"message": "synthetic secret shape"}, session_id="s1")
        self.assertEqual(review["action"], "approve")

    def test_mcp_permission_deny_overrides_another_grant(self):
        grant = self.make_hook("grant.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'allow'}}}))\n")
        deny = self.make_hook("deny.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest','decision':{'behavior':'deny','reason':'Sensitive egress'}}}))\n")
        bridge = self.bridge({"PermissionRequest": [{"matcher": "mcp__.*", "hooks": [
            {"type": "command", "command": grant}, {"type": "command", "command": deny},
        ]}]})
        self.assertEqual(
            bridge.pre_tool_call("mcp__example__send", {"message": "test"}, session_id="s1"),
            {"action": "block", "message": "Sensitive egress"},
        )

    def test_session_end_registers_on_actual_session_boundary(self):
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"SessionEnd": []}}))
        hooks = {}

        class Context:
            def register_hook(self, name, callback):
                hooks[name] = callback

        plugin_root = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge"
        specification = importlib.util.spec_from_file_location(
            "lifeos_fixture_plugin", plugin_root / "__init__.py",
            submodule_search_locations=[str(plugin_root)],
        )
        module = importlib.util.module_from_spec(specification)
        sys.modules[specification.name] = module
        self.addCleanup(sys.modules.pop, specification.name, None)
        specification.loader.exec_module(module)
        with patch.dict(os.environ, {"LIFEOS_HOOK_SETTINGS": str(settings)}):
            module.register(Context())
        self.assertIn("on_session_finalize", hooks)
        self.assertIn("on_turn_result", hooks)
        self.assertNotIn("on_session_reset", hooks)

    def test_stop_failure_logs_only_terminal_api_error(self):
        marker = self.root / "stop-failure.json"
        command = self.make_hook(
            "stop_failure.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(json.dumps(data))\n",
        )
        bridge = self.bridge({"StopFailure": [{"hooks": [{"type": "command", "command": command}]}]})
        bridge.api_request_error(
            session_id="s1", turn_id="turn-1", reason="rate_limit",
            error={"type": "RateLimitError", "message": "429 synthetic limit"},
        )
        bridge.turn_end(session_id="s1", turn_id="turn-1", failed=False, turn_exit_reason="text_response")
        self.assertFalse(marker.exists())
        bridge.api_request_error(
            session_id="s1", turn_id="turn-2", reason="rate_limit",
            error={"type": "RateLimitError", "message": "429 synthetic limit"},
        )
        bridge.turn_end(
            session_id="s1", turn_id="turn-2", failed=True,
            turn_exit_reason="all_retries_exhausted_no_response",
        )
        payload = json.loads(marker.read_text())
        self.assertEqual(payload["hook_event_name"], "StopFailure")
        self.assertEqual(payload["error"], "rate_limit")
        self.assertEqual(payload["error_details"], "429 synthetic limit")

    def test_stop_failure_logs_direct_terminal_api_error(self):
        marker = self.root / "direct-api-failure.json"
        command = self.make_hook(
            "record-direct-failure.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(json.dumps(data))\n",
        )
        bridge = self.bridge({"StopFailure": [{"hooks": [{"type": "command", "command": command}]}]})
        bridge.api_request_error(
            session_id="s1", turn_id="turn-1", reason="auth_permanent",
            error={"message": "401 synthetic rejection"},
        )
        bridge.turn_end(
            session_id="s1", turn_id="turn-1", failed=True,
            failure_reason="auth_permanent", final_response="Provider rejected the request",
        )
        payload = json.loads(marker.read_text())
        self.assertEqual(payload["error"], "authentication_failed")
        self.assertEqual(payload["last_assistant_message"], "Provider rejected the request")

    def test_prior_api_error_does_not_turn_local_failure_into_stop_failure(self):
        marker = self.root / "wrong-stop-failure"
        command = self.make_hook("record.py", f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
        bridge = self.bridge({"StopFailure": [{"hooks": [{"type": "command", "command": command}]}]})
        bridge.api_request_error(
            session_id="s1", turn_id="turn-1", reason="rate_limit", error={"message": "429"},
        )
        bridge.turn_end(session_id="s1", turn_id="turn-1", failed=True, failure_reason="loop_error")
        self.assertFalse(marker.exists())

    def test_config_change_runs_audit_hook_after_settings_edit(self):
        marker = self.root / "config-change.json"
        command = self.make_hook(
            "config_change.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(json.dumps(data))\n",
        )
        bridge = self.bridge({"ConfigChange": [{"hooks": [{"type": "command", "command": command}]}]})
        bridge.pre_llm_call("first", session_id="s1")
        bridge.poll_config_changes(force=True)
        self.assertFalse(marker.exists())
        settings = json.loads(bridge.settings_path.read_text())
        settings["env"] = {"SYNTHETIC_CONFIG_VALUE": "changed"}
        bridge.settings_path.write_text(json.dumps(settings))
        bridge.poll_config_changes(force=True)
        payload = json.loads(marker.read_text())
        self.assertEqual(payload["hook_event_name"], "ConfigChange")
        self.assertEqual(payload["config_path"], payload["file_path"])
        self.assertEqual(payload["source"], "user_settings")
        self.assertEqual(payload["file_path"], str(bridge.settings_path))

    def test_settings_change_updates_hook_registrations(self):
        first = self.make_hook("first_tool.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'updatedInput':{'command':'echo first'}}}))\n")
        second = self.make_hook("second_tool.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'updatedInput':{'command':'echo second'}}}))\n")
        bridge = self.bridge({"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": first}]}]})
        self.assertEqual(bridge.pre_tool_call("terminal", {"command": "echo input"}, session_id="s1")["args"]["command"], "echo first")
        bridge.settings_path.write_text(json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": second}]}],
        }}))
        bridge.poll_config_changes(force=True)
        self.assertEqual(bridge.pre_tool_call("terminal", {"command": "echo input"}, session_id="s1")["args"]["command"], "echo second")

    def test_config_change_block_keeps_active_hook_settings(self):
        gate = self.make_hook("config_block.py", "import json\nprint(json.dumps({'decision':'block'}))\n")
        first = self.make_hook("first.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'updatedInput':{'command':'echo first'}}}))\n")
        second = self.make_hook("second.py", "import json\nprint(json.dumps({'hookSpecificOutput':{'updatedInput':{'command':'echo second'}}}))\n")
        settings_hooks = {
            "ConfigChange": [{"hooks": [{"type": "command", "command": gate}]}],
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": first}]}],
        }
        bridge = self.bridge(settings_hooks)
        bridge.pre_llm_call("first", session_id="s1")
        settings_hooks["PreToolUse"][0]["hooks"][0]["command"] = second
        bridge.settings_path.write_text(json.dumps({"hooks": settings_hooks}))
        bridge.poll_config_changes(force=True)
        self.assertEqual(bridge.pre_tool_call("terminal", {"command": "echo input"}, session_id="s1")["args"]["command"], "echo first")

    def test_clarify_maps_to_ask_user_question_hooks(self):
        marker = self.root / "question-events.jsonl"
        command = self.make_hook(
            "question.py",
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(marker)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n",
        )
        bridge = self.bridge({
            "PreToolUse": [{"matcher": "AskUserQuestion", "hooks": [{"type": "command", "command": command}]}],
            "PostToolUse": [{"matcher": "AskUserQuestion", "hooks": [{"type": "command", "command": command}]}],
        })
        args = {"questions": [{"question": "Which option works?", "choices": ["A", "B"]}]}
        bridge.pre_tool_call("clarify", args, session_id="s1")
        bridge.post_tool_call("clarify", args, "A", session_id="s1")
        events = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual([event["hook_event_name"] for event in events], ["PreToolUse", "PostToolUse"])
        self.assertTrue(all(event["tool_name"] == "AskUserQuestion" for event in events))
        self.assertEqual(events[0]["tool_input"]["questions"][0]["question"], "Which option works?")

    def test_multi_file_patch_checks_each_changed_file(self):
        command = self.make_hook(
            "patch_guard.py",
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            "entry=data['tool_input']\n"
            "if entry.get('file_path')=='/tmp/second.txt' and 'SENSITIVE' in entry.get('new_string',''):\n"
            " print('blocked second file',file=sys.stderr)\n sys.exit(2)\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": command}]}]})
        patch_text = """*** Begin Patch
*** Update File: /tmp/first.txt
@@
-old
+safe
*** Update File: /tmp/second.txt
@@
-old
+SENSITIVE
*** End Patch"""
        result = bridge.pre_tool_call("patch", {"mode": "patch", "patch": patch_text}, session_id="s1")
        self.assertEqual(result, {"action": "block", "message": "blocked second file"})

    def test_hook_process_uses_agent_working_directory(self):
        marker = self.root / "cwd.json"
        command = self.make_hook(
            "cwd.py",
            "import json,os,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"Path({str(marker)!r}).write_text(json.dumps({{'process':os.getcwd(),'payload':data['cwd']}}))\n",
        )
        bridge = self.bridge({"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]})
        bridge.pre_tool_call("terminal", {"command": "echo test"}, session_id="s1")
        location = json.loads(marker.read_text())
        self.assertEqual(location, {"process": str(Path.cwd()), "payload": str(Path.cwd())})


if __name__ == "__main__":
    unittest.main()
