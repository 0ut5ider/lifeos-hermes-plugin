# ABOUTME: Checks native LifeOS failure capture against a bridge transcript.
# ABOUTME: Keeps inference and all output inside a disposable test directory.

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


CAPTURE_PATH = os.environ.get("LIFEOS_FAILURE_CAPTURE_PATH")


@unittest.skipUnless(CAPTURE_PATH and shutil.which("bun"), "LifeOS FailureCapture and Bun are required")
class NativeFailureCaptureTests(unittest.TestCase):
    def test_tool_result_is_attached_to_call_not_user_text(self):
        with tempfile.TemporaryDirectory(prefix="failure-capture-parity-") as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text('{"hooks":{}}')
            bridge = HookBridge(settings, root)
            try:
                bridge.pre_llm_call("Try the command", session_id="failure-capture-probe")
                bridge.post_tool_call(
                    "terminal", {"command": "printf proof"}, "tool output confirmed",
                    session_id="failure-capture-probe", tool_call_id="tool-1",
                )
                bridge.post_tool_call(
                    "read_file", {"path": str(root / "proof.txt")}, "second tool output",
                    session_id="failure-capture-probe", tool_call_id="tool-2",
                )
                bridge.stop("I missed the result", session_id="failure-capture-probe")

                bin_dir = root / "bin"
                bin_dir.mkdir()
                claude = bin_dir / "claude"
                claude.write_text(
                    '#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" '
                    "'{\"result\":\"synthetic-failure-description\",\"is_error\":false}'\n"
                )
                claude.chmod(0o755)
                script = (
                    f'import {{captureFailure}} from "{CAPTURE_PATH}"; '
                    'await captureFailure({'
                    f'transcriptPath: "{bridge.transcript_path("failure-capture-probe")}", '
                    'rating: 2, sentimentSummary: "Test correction", '
                    'sessionId: "failure-capture-probe"});'
                )
                environment = {
                    **os.environ,
                    "LIFEOS_DIR": str(root / "LIFEOS"),
                    "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                }
                process = subprocess.run(
                    ["bun", "-e", script], capture_output=True, text=True,
                    env=environment, timeout=20,
                )
            finally:
                bridge.close()

            self.assertEqual(process.returncode, 0, process.stderr)
            captures = list((root / "LIFEOS/MEMORY/LEARNING/FAILURES").glob("**/tool-calls.json"))
            self.assertEqual(len(captures), 1)
            calls = json.loads(captures[0].read_text())
            self.assertEqual(calls[0]["name"], "Bash")
            self.assertEqual(calls[0]["output"], "tool output confirmed")
            self.assertEqual(calls[1]["name"], "Read")
            self.assertEqual(calls[1]["output"], "second tool output")
            context = (captures[0].parent / "CONTEXT.md").read_text()
            self.assertNotIn("**USER:** tool output confirmed", context)
            self.assertNotIn("**USER:** second tool output", context)
