# ABOUTME: Verifies native delegation records with trusted Hermes request metadata.
# ABOUTME: Runs the installed AgentInvocation program in disposable synthetic homes.

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HOOK_PATH = os.environ.get("LIFEOS_AGENT_INVOCATION_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS AgentInvocation and Bun are required")
class NativeAgentInvocationTests(unittest.TestCase):
    def run_dispatch(self, model=None, runtime=None, transcript_model=None):
        temporary = tempfile.TemporaryDirectory(prefix="lifeos-agent-invocation-")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        lifeos = home / ".claude/LIFEOS"
        lifeos.mkdir(parents=True)
        transcript = home / "transcript.jsonl"
        if transcript_model:
            transcript.write_text(json.dumps({"type": "assistant", "message": {"model": transcript_model}}) + "\n")
        payload = {"hook_event_name": "PreToolUse", "session_id": "parent-session", "tool_name": "Agent",
                   "transcript_path": str(transcript), "tool_input": {
                       "subagent_type": "general-purpose", "description": "Inspect report", "prompt": "Read the report"}}
        if model:
            payload["tool_input"]["model"] = model
        if runtime is not None:
            payload["hermes_runtime"] = runtime
        environment = {**os.environ, "HOME": str(home), "LIFEOS_DIR": str(lifeos)}
        run = lambda data: subprocess.run(["bun", HOOK_PATH], input=json.dumps(data), env=environment,
                                         text=True, capture_output=True, timeout=20)
        pre = run(payload)
        self.assertEqual(pre.returncode, 0, pre.stderr)
        self.assertEqual(pre.stdout, "")
        self.assertIn("[AgentInvocation] START", pre.stderr)
        starts = json.loads((lifeos / "MEMORY/OBSERVABILITY/agent-starts.json").read_text())
        self.assertEqual(list(starts), ["parent-session::Inspect report"])
        post = run({**payload, "hook_event_name": "PostToolUse", "tool_response": "Report inspected"})
        self.assertEqual(post.returncode, 0, post.stderr)
        self.assertEqual(post.stdout, "")
        self.assertIn("[AgentInvocation] STOP", post.stderr)
        self.assertEqual(json.loads((lifeos / "MEMORY/OBSERVABILITY/agent-starts.json").read_text()), {})
        rows = [json.loads(line) for line in (lifeos / "MEMORY/OBSERVABILITY/subagent-events.jsonl").read_text().splitlines()]
        self.assertEqual([row["event"] for row in rows], ["subagent_start", "subagent_stop"])
        self.assertEqual(rows[0]["subagent_id"], rows[1]["subagent_id"])
        return rows

    def test_current_request_resolves_inheritance_before_transcript_write(self):
        rows = self.run_dispatch(runtime={"model": "current-model", "provider": "private"}, transcript_model="stale-model")
        self.assertEqual((rows[0]["subagent_model"], rows[0]["subagent_level"]), ("current-model", "session-inherited"))

    def test_explicit_tier_keeps_its_precedence(self):
        rows = self.run_dispatch(model="opus", runtime={"model": "current-model"})
        self.assertEqual(rows[0]["subagent_model"], "opus")
        self.assertNotEqual(rows[0]["subagent_level"], "session-inherited")

    def test_native_transcript_still_resolves_inheritance(self):
        rows = self.run_dispatch(transcript_model="native-model")
        self.assertEqual((rows[0]["subagent_model"], rows[0]["subagent_level"]), ("native-model", "session-inherited"))

    def test_invalid_runtime_keeps_an_unknown_carrier_honest(self):
        for runtime in ({"model": None}, {"model": "  "}, "spoofed"):
            with self.subTest(runtime=runtime):
                rows = self.run_dispatch(runtime=runtime)
                self.assertEqual((rows[0]["subagent_model"], rows[0]["subagent_level"]), ("inherited", "session"))
