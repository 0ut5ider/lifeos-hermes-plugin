# ABOUTME: Checks temporary trace wrappers for paired native and Hermes hook runs.
# ABOUTME: Verifies exact command forwarding and safe restoration of hook settings.

import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.paired_hook_trace import instrument, restore, run_hook


class PairedHookTraceTests(unittest.TestCase):
    def test_instruments_coalesced_hooks_and_restores_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "hooks.json"
            settings = root / "settings.json"
            manifest.write_text(json.dumps({"hooks": {"Stop": [
                {"hooks": [{"type": "command", "command": "printf one"}]},
                {"hooks": [{"type": "command", "command": "printf two"}]},
            ]}}))
            settings.write_text(json.dumps({"hooks": {"Stop": [{"matcher": "", "hooks": [
                {"type": "command", "command": "printf one"},
                {"type": "command", "command": "printf two"},
                {"type": "command", "command": "printf foreign"},
            ]}]}}))
            before = settings.read_bytes()
            report = instrument(manifest, settings, root / "trace.jsonl")
            self.assertEqual(report["wrapped"], 2)
            hooks = json.loads(settings.read_text())["hooks"]["Stop"][0]["hooks"]
            self.assertIn("Stop.1.1", hooks[0]["command"])
            self.assertIn("Stop.2.1", hooks[1]["command"])
            self.assertEqual(hooks[2]["command"], "printf foreign")
            restore(settings)
            self.assertEqual(settings.read_bytes(), before)

    def test_wrapper_forwards_output_exit_code_and_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            command = 'cat; printf warning >&2; exit 2'
            encoded = base64.b64encode(command.encode()).decode()
            result = subprocess.run(["python3", "scripts/paired_hook_trace.py", "run", "Stop.1.1",
                                     str(trace), encoded], input=b'{"hook_event_name":"Stop"}',
                                    capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'{"hook_event_name":"Stop"}')
            self.assertEqual(result.stderr, b'warning')
            row = json.loads(trace.read_text().splitlines()[0])
            self.assertEqual(row["id"], "Stop.1.1")
            self.assertEqual(row["exit_code"], 2)

    def test_trace_retains_exact_input_for_effect_comparisons(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            request = b'{"tool_input":{"query":"fixture"}, "tool_response":{"content":[{"type":"tool_reference","tool_name":"mcp__paired__ping"}]}}\n'
            result = subprocess.run(
                ["python3", "scripts/paired_hook_trace.py", "run", "PostToolUse.5.1",
                 str(trace), base64.b64encode(b"cat").decode()],
                input=request, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, request)
            row = json.loads(trace.read_text())
            self.assertEqual(base64.b64decode(row["stdin_base64"]), request)
            self.assertEqual(trace.stat().st_mode & 0o777, 0o600)
