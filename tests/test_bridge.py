# ABOUTME: Tests native LifeOS hook execution through the Hermes event bridge.
# ABOUTME: Uses real child processes and Claude hook JSON contracts.

import json
import importlib.util
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from bridge import HookBridge


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
        return HookBridge(settings, self.root)

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
        self.assertIsNone(bridge.pre_tool_call("todo_list", valid, session_id="s1"))
        self.assertIsNone(bridge.pre_tool_call("todo_list", valid, session_id="s1"))
        self.assertEqual(bridge.task_counts["s1"], 1)

        other = {"todos": [
            {"id": f"task-{number}", "content": f"Meaningful task {number}", "status": "pending"}
            for number in range(2, 51)
        ]}
        self.assertIsNone(bridge.pre_tool_call("todo_list", other, session_id="s1"))
        over_limit = {"todos": [{"id": "task-51", "content": "Meaningful task 51", "status": "pending"}]}
        self.assertIn("limit of 50", bridge.pre_tool_call("todo_list", over_limit, session_id="s1")["message"])

    def test_kanban_task_creation_uses_same_lifeos_limit(self):
        bridge = self.bridge({"TaskCreated": [{"hooks": [{"type": "command", "command": "true"}]}]})
        short = bridge.pre_tool_call("kanban_create", {"title": "short", "assignee": "worker"}, session_id="s1")
        self.assertEqual(short["action"], "block")
        valid = {"title": "Meaningful task title", "body": "Describe the work", "assignee": "worker"}
        for _ in range(50):
            self.assertIsNone(bridge.pre_tool_call("kanban_create", valid, session_id="s1"))
        self.assertIn("limit of 50", bridge.pre_tool_call("kanban_create", valid, session_id="s1")["message"])

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

    def test_session_end_registers_on_actual_session_boundary(self):
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"SessionEnd": []}}))
        hooks = {}

        class Context:
            def register_hook(self, name, callback):
                hooks[name] = callback

        plugin_root = Path(__file__).resolve().parents[1]
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
        self.assertIn("on_session_end", hooks)
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
