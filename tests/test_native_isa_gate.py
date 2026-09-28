# ABOUTME: Checks the installed LifeOS ISA structural Stop gate through the bridge.
# ABOUTME: Uses a disposable ISA and transcript to verify a native block decision.

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lifeos_hook_bridge.bridge import HookBridge


class NativeISAGateTests(unittest.TestCase):
    def test_closed_isa_with_hard_violations_blocks_stop(self):
        home = Path.home()
        bun = home / ".bun/bin/bun"
        hook = home / ".claude/hooks/StopGates.hook.ts"
        if not bun.exists() or not hook.exists():
            self.skipTest("installed LifeOS StopGates and Bun are required")

        with TemporaryDirectory(prefix="isa-stop-parity-") as directory:
            root = Path(directory)
            isa = root / "ISA.md"
            content = (
                "---\nphase: complete\nprogress: done\n---\n\n"
                "## Not yet specified\n- unresolved question\n"
            )
            isa.write_text(content)
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": f"{bun} {hook}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            try:
                bridge.pre_llm_call("Close this ISA", session_id="isa-stop-probe")
                bridge.post_tool_call(
                    "write_file", {"path": str(isa), "content": content}, "wrote file",
                    session_id="isa-stop-probe", tool_call_id="write-isa",
                )
                result = bridge.stop("", session_id="isa-stop-probe")
            finally:
                bridge.close()

            self.assertIsNotNone(result)
            self.assertEqual(result["action"], "continue")
            self.assertIn("progress-format", result["message"])
            self.assertIn("fog-at-complete", result["message"])
