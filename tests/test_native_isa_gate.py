# ABOUTME: Checks the installed LifeOS ISA structural Stop gate through the bridge.
# ABOUTME: Uses a disposable ISA and transcript to verify a native block decision.

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lifeos_hook_bridge.bridge import HookBridge


class NativeISAGateTests(unittest.TestCase):
    def active_run(self, root, session_id):
        state = root / "LIFEOS/MEMORY/STATE"
        state.mkdir(parents=True)
        (state / "work.json").write_text(json.dumps({"sessions": {"sample-run": {
            "sessionUUID": session_id,
            "phase": "climbing",
            "started": "2026-09-27T00:00:00Z",
            "isa": str(root / "LIFEOS/MEMORY/WORK/sample-run/ISA.md"),
        }}}))
        return state

    def bridge_with_stop_hook(self, root, command):
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": command},
        ]}]}}))
        return HookBridge(settings, root)

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
            bridge = self.bridge_with_stop_hook(root, f"{bun} {hook}")
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

    def test_stale_isa_blocks_completion_claim(self):
        home = Path.home()
        bun = home / ".bun/bin/bun"
        hook = home / ".claude/hooks/ISACloseGate.hook.ts"
        if not bun.exists() or not hook.exists():
            self.skipTest("installed LifeOS ISACloseGate and Bun are required")

        with TemporaryDirectory(prefix="isa-close-parity-") as directory:
            root = Path(directory)
            session_id = "isa-close-probe"
            state = self.active_run(root, session_id)
            nudge = state / "isa-nudge"
            nudge.mkdir()
            (nudge / f"{session_id}.json").write_text(json.dumps({"toolCallsSinceISAEditAbs": 11}))
            driver = root / "run-close.ts"
            driver.write_text(
                f'import {{run}} from "{hook}"; '
                'const input=JSON.parse(await Bun.stdin.text()); '
                'const out=await run(input); if(out) console.log(JSON.stringify(out));\n'
            )
            bridge = self.bridge_with_stop_hook(root, f"{bun} {driver}")
            try:
                bridge.pre_llm_call("Finish the task", session_id=session_id)
                bridge.post_tool_call(
                    "terminal", {"command": "echo evidence"}, "evidence",
                    session_id=session_id, tool_call_id="bash-1",
                )
                result = bridge.stop("Done.", session_id=session_id)
            finally:
                bridge.close()

            self.assertIsNotNone(result)
            self.assertEqual(result["action"], "continue")
            self.assertIn("ISA CLOSE GAP", result["message"])

    def test_production_mutation_without_isa_edit_blocks_stop(self):
        home = Path.home()
        bun = home / ".bun/bin/bun"
        hook = home / ".claude/hooks/StopGates.hook.ts"
        if not bun.exists() or not hook.exists():
            self.skipTest("installed LifeOS StopGates and Bun are required")

        with TemporaryDirectory(prefix="isa-fold-parity-") as directory:
            root = Path(directory)
            session_id = "isa-fold-probe"
            self.active_run(root, session_id)
            bridge = self.bridge_with_stop_hook(root, f"{bun} {hook}")
            try:
                bridge.pre_llm_call("Update deployment", session_id=session_id)
                bridge.post_tool_call(
                    "terminal", {"command": "wrangler secret put TEST_SECRET"}, "success",
                    session_id=session_id, tool_call_id="bash-1",
                )
                result = bridge.stop("", session_id=session_id)
            finally:
                bridge.close()

            self.assertIsNotNone(result)
            self.assertEqual(result["action"], "continue")
            self.assertIn("ISA FOLD GAP", result["message"])
