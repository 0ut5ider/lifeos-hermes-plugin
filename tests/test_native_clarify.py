# ABOUTME: Verifies waiting and restoration hooks with the real Hermes clarification queue.
# ABOUTME: Compares native hook state in disposable homes without connecting to Discord.

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from queue import Queue
import unittest

from lifeos_hook_bridge.bridge import HookBridge, _tool_input


SOURCE = os.environ.get("LIFEOS_TAB_STATE_SOURCE")


@unittest.skipUnless(SOURCE and shutil.which("bun"), "Native TabState and Bun are required")
class NativeClarifyTests(unittest.TestCase):
    def fixture(self, folder, hook):
        root = folder / ".claude"
        state = root / "LIFEOS/MEMORY/STATE/tab-titles/777.json"
        state.parent.mkdir(parents=True)
        prior = {"title": "Inspecting report", "state": "working", "ascent": "traverse"}
        state.write_text(json.dumps(prior))
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": {event: [{"matcher": "AskUserQuestion", "hooks": [
            {"type": "command", "command": f"bun {hook}"}]}] for event in ("PreToolUse", "PostToolUse")}}))
        environment = {**os.environ, "HOME": str(folder), "LIFEOS_DIR": str(root / "LIFEOS"),
                       "LIFEOS_NOTIFICATION_CHANNEL": "desktop", "KITTY_WINDOW_ID": "777",
                       "KITTY_LISTEN_ON": f"unix:{folder}/absent-kitty.sock", "TERM": "xterm-kitty"}
        return root, state, environment

    def round_trip(self, outcome, count=1, single=False):
        from tools import clarify_gateway as queue
        from tools.clarify_tool import clarify_tool

        with tempfile.TemporaryDirectory(prefix="lifeos-clarify-") as directory:
            home = Path(directory)
            source = Path(SOURCE)
            root, state, environment = self.fixture(home / "hermes", source / "hooks/TabState.hook.ts")
            native_root, native_state, native_environment = self.fixture(home / "native", source / "hooks/TabState.hook.ts")
            bridge = HookBridge(root / "settings.json", root, lifeos_home=home / "hermes")
            bridge.environment.update(environment)
            self.addCleanup(bridge.close)
            args = {"question": "Fixture batch title", "questions": [
                {"question": "Choose the fixture mode " + str(index), "choices": ["A", "B"]} for index in range(count)]}
            if single:
                args = {"question": "Choose the fixture mode", "choices": ["A", "B"]}
            native_input = _tool_input("AskUserQuestion", args, str(home), "")
            payload = {"tool_name": "AskUserQuestion", "tool_input": native_input,
                       "session_id": "fixture-parent", "transcript_path": str(home / "unused-transcript")}

            def native(event):
                result = subprocess.run(["bun", str(source / "hooks/TabState.hook.ts")],
                                        input=json.dumps({**payload, "hook_event_name": event}),
                                        env=native_environment, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn(f"[TabState/{event}]", result.stderr)

            def comparable(path):
                value = json.loads(path.read_text())
                value.pop("timestamp", None)
                return value

            native("PreToolUse")
            self.assertIsNone(bridge.pre_tool_call("clarify", args, session_id="fixture-parent", tool_call_id="question-1"))
            waiting = comparable(state)
            self.assertEqual(waiting, comparable(native_state))
            self.assertEqual(waiting["activity"], "waiting")
            self.assertEqual(waiting["previousTitle"], "Inspecting report")
            self.assertIn("Choose the fixture", waiting["title"])
            self.assertNotIn("batch title", waiting["title"])
            pending = Queue()
            entries = []
            entry_id = "fixture-question-" + outcome

            def adapter(question, choices, multi_select=False):
                current_id = entry_id + "-" + str(len(entries))
                entries.append(current_id)
                queue.register(current_id, "fixture-chat", question, choices, multi_select)
                pending.put(current_id)
                return queue.wait_for_response(current_id, 0.1 if outcome == "timeout" else 5)

            try:
                with ThreadPoolExecutor(max_workers=1) as worker:
                    result = worker.submit(clarify_tool, **args, callback=adapter)
                    for index in range(count if outcome == "answer" else 1):
                        current_id = pending.get(timeout=5)
                        self.assertFalse(result.done())
                        if outcome == "answer":
                            self.assertTrue(queue.resolve_gateway_clarify(current_id, "A"))
                            self.assertFalse(queue.resolve_gateway_clarify(current_id, "B"))
                        elif outcome == "cancel":
                            self.assertEqual(queue.clear_session("fixture-chat"), 1)
                    returned = result.result(timeout=6)
                data = json.loads(returned)
                responses = [data] if single else data["responses"]
                self.assertEqual(len(responses), count)
                self.assertTrue(all(row["user_response"] == ("A" if outcome == "answer" else "") for row in responses), data)
                self.assertEqual(bool(data.get("timed_out")), outcome == "timeout")
                bridge.post_tool_call("clarify", args, returned, session_id="fixture-parent", tool_call_id="question-1")
                native("PostToolUse")
                restored = comparable(state)
                self.assertEqual(restored, comparable(native_state))
                self.assertEqual(restored["ascent"], "traverse")
                self.assertIn("Inspecting report", restored["title"])
                self.assertNotIn("activity", restored)
                self.assertNotIn("previousTitle", restored)
                self.assertIsNone(queue.get_pending_for_session("fixture-chat", include_choice_prompts=True))
                self.assertTrue(all(not queue.resolve_gateway_clarify(current_id, "late answer") for current_id in entries))
            finally:
                queue.clear_session("fixture-chat")

    def test_answer_and_duplicate_reply_restore_the_prior_state(self):
        self.round_trip("answer")

    def test_timeout_restores_the_prior_state_and_discards_late_answers(self):
        self.round_trip("timeout")

    def test_cancel_restores_the_prior_state_without_reopening_the_prompt(self):
        self.round_trip("cancel")

    def test_two_independent_questions_restore_the_same_prior_state(self):
        self.round_trip("answer", count=2)

    def test_single_question_restores_the_prior_state(self):
        self.round_trip("answer", single=True)

    def test_finalization_clears_pending_question_and_resets_only_desktop_state(self):
        from tools import clarify_gateway as queue
        for platform in ('cli', 'discord'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                root, state, environment = self.fixture(home, Path(SOURCE)/'hooks/TabState.hook.ts')
                settings = json.loads((root/'settings.json').read_text())
                settings['hooks']['SessionEnd'] = [{'hooks':[{'type':'command',
                    'command': 'bun '+str(Path(SOURCE)/'hooks/SessionCleanup.hook.ts')}]}]
                (root/'settings.json').write_text(json.dumps(settings))
                bridge = HookBridge(root/'settings.json', root, lifeos_home=home)
                self.addCleanup(bridge.close)
                bridge.environment.update(environment)
                bridge.environment['LIFEOS_NOTIFICATION_CHANNEL'] = 'desktop' if platform == 'cli' else 'discord'
                bridge.session_platforms['ending'] = platform
                prior = state.read_bytes()
                other = state.with_name('778.json')
                other.write_bytes(prior)
                bridge.pre_tool_call('clarify', {'question':'Choose the fixture mode'}, session_id='ending')
                queue.register('ending-question', 'ending', 'Choose the fixture mode', None)
                bridge.session_end(session_id='ending', reason='prompt_input_exit')
                self.assertEqual(queue.clear_session('ending'), 1)
                self.assertEqual(queue.wait_for_response('ending-question', .1), None)
                self.assertFalse(queue.resolve_gateway_clarify('ending-question', 'late'))
                if platform == 'discord':
                    self.assertEqual(state.read_bytes(), prior)
                else:
                    self.assertFalse(state.exists())
                self.assertEqual(other.read_bytes(), prior)
