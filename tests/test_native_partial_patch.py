# ABOUTME: Checks LifeOS Edit effects after a real Hermes patch partially applies.
# ABOUTME: Uses disposable files and the installed native complexity hook.

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


class NativePartialPatchTests(unittest.TestCase):
    def test_successful_edit_still_reaches_native_hook_after_later_failure(self):
        try:
            from tools.patch_parser import apply_v4a_operations, parse_v4a_patch
        except ImportError:
            self.skipTest("Hermes patch parser is required")
        home = Path.home()
        bun = shutil.which("bun")
        hook = home / ".claude/hooks/ComplexityRatchet.hook.ts"
        if not bun or not hook.exists():
            self.skipTest("installed LifeOS complexity hook and Bun are required")

        with tempfile.TemporaryDirectory(prefix="partial-patch-parity-") as directory:
            root = Path(directory)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_text("old-first")
            second.write_text("old-second")
            added_lines = [f"line {index}" for index in range(250)]
            patch_text = (
                "*** Begin Patch\n"
                f"*** Update File: {first}\n-old-first\n"
                + "".join(f"+{line}\n" for line in added_lines)
                + f"*** Update File: {second}\n-old-second\n+new-second\n"
                "*** End Patch"
            )

            class FileOps:
                def read_file_raw(self, path):
                    target = Path(path)
                    if not target.exists():
                        return SimpleNamespace(content="", error="not found", not_found=True)
                    return SimpleNamespace(content=target.read_text(), error=None, not_found=False)

                def write_file(self, path, content, pre_content=None):
                    if path == str(second):
                        return SimpleNamespace(error="forced second write failure")
                    Path(path).write_text(content)
                    return SimpleNamespace(error=None, lsp_diagnostics=None, lint=None)

            operations, parse_error = parse_v4a_patch(patch_text)
            self.assertIsNone(parse_error)
            outcome = apply_v4a_operations(operations, FileOps())
            self.assertFalse(outcome.success)
            self.assertEqual(outcome.files_modified, [str(first)])
            self.assertIn("line 249", first.read_text())
            self.assertEqual(second.read_text(), "old-second")

            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"PostToolUse": [{
                "matcher": "Edit", "hooks": [{"type": "command", "command": f"{bun} {hook}"}],
            }]}}))
            lifeos_dir = root / "home/.claude/LIFEOS"
            lifeos_dir.parent.mkdir(parents=True)
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {
                    "HOME": str(root / "home"), "LIFEOS_DIR": str(lifeos_dir),
                    "CLAUDE_PLUGIN_ROOT": "",
                }):
                    bridge = HookBridge(settings, root)
                    try:
                        result_text = json.dumps(outcome.to_dict())
                        context = bridge.augment_tool_result(
                            "patch", {"mode": "patch", "patch": patch_text},
                            result_text, original_result=result_text, session_id="partial-patch-native",
                            tool_call_id="patch-1", status="error", error_message=outcome.error or "",
                        )
                        state = json.loads((lifeos_dir / "MEMORY/STATE/complexity-ratchet"
                                            / "partial-patch-native.json").read_text())
                        self.assertEqual(state["cumulative"], 249)
                        self.assertIn("COMPLEXITY RATCHET", context or "")
                        rows = [json.loads(line) for line in bridge.transcript_path("partial-patch-native").read_text().splitlines()]
                        results = rows[-1]["message"]["content"]
                        self.assertEqual([item["is_error"] for item in results], [False, True])
                    finally:
                        bridge.close()
            finally:
                os.chdir(previous_cwd)

    def test_failed_patch_does_not_checkpoint_an_earlier_isa_edit(self):
        home = Path.home()
        source = home / "workspace/lifeos-candidate"
        bun = shutil.which("bun")
        hook = home / ".claude/hooks/CheckpointPerISC.hook.ts"
        if not (source / ".git").exists() or not bun or not hook.exists():
            self.skipTest("installed LifeOS checkout, checkpoint hook, and Bun are required")

        with tempfile.TemporaryDirectory(prefix="partial-checkpoint-parity-") as directory:
            root = Path(directory)
            repo = root / "repo"
            subprocess.run(
                ["git", "-C", str(source), "worktree", "add", "--detach", str(repo), "HEAD"],
                check=True, capture_output=True, text=True,
            )
            try:
                before = subprocess.run(
                    ["git", "-C", str(repo), "rev-parse", "HEAD"],
                    check=True, capture_output=True, text=True,
                ).stdout.strip()
                (repo / "partial-proof.txt").write_text("not complete")
                test_home = root / "home"
                claude = test_home / ".claude"
                isa = claude / "LIFEOS/MEMORY/WORK/partial-claim/ISA.md"
                isa.parent.mkdir(parents=True)
                started = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
                isa.write_text(
                    f"---\ntitle: Partial claim\nstarted: {started}\n---\n\n"
                    "## Claims\n- [x] ISC-1: Requires the later file\n"
                )
                (claude / "checkpoint-repos.txt").write_text(f"{repo}\n")
                (claude / "hooks").symlink_to(hook.parent, target_is_directory=True)
                settings = root / "settings.json"
                settings.write_text(json.dumps({"hooks": {"PostToolUse": [{
                    "matcher": "Edit", "hooks": [{
                        "type": "command", "command": "$HOME/.claude/hooks/CheckpointPerISC.hook.ts",
                    }],
                }]}}))
                patch_text = (
                    "*** Begin Patch\n"
                    f"*** Update File: {isa}\n- [ ] ISC-1: Requires the later file\n"
                    "+ [x] ISC-1: Requires the later file\n"
                    f"*** Update File: {repo / 'partial-proof.txt'}\n-not complete\n+complete\n"
                    "*** End Patch"
                )
                outcome = json.dumps({
                    "success": False, "error": "forced later failure",
                    "files_modified": [str(isa)],
                })
                previous_cwd = Path.cwd()
                try:
                    os.chdir(root)
                    with patch.dict(os.environ, {
                        "HOME": str(test_home), "LIFEOS_DIR": str(claude / "LIFEOS"),
                        "CLAUDE_PLUGIN_ROOT": "",
                        "GIT_AUTHOR_NAME": "Parity Probe", "GIT_AUTHOR_EMAIL": "probe@example.invalid",
                        "GIT_COMMITTER_NAME": "Parity Probe", "GIT_COMMITTER_EMAIL": "probe@example.invalid",
                    }):
                        bridge = HookBridge(settings, root)
                        try:
                            bridge.augment_tool_result(
                                "patch", {"mode": "patch", "patch": patch_text}, outcome,
                                original_result=outcome, session_id="partial-checkpoint",
                                status="error", error_message="forced later failure",
                            )
                            after_failure = subprocess.run(
                                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True,
                            ).stdout.strip()
                            self.assertEqual(after_failure, before)
                            state_path = isa.parent / ".checkpoint-state.json"
                            if state_path.exists():
                                self.assertNotIn("ISC-1", json.loads(state_path.read_text())["committed_iscs"])

                            (repo / "partial-proof.txt").write_text("complete")
                            success = json.dumps({
                                "success": True,
                                "files_modified": [str(isa), str(repo / "partial-proof.txt")],
                            })
                            bridge.augment_tool_result(
                                "patch", {"mode": "patch", "patch": patch_text}, success,
                                original_result=success, session_id="partial-checkpoint",
                                status="ok",
                            )
                            after_success = subprocess.run(
                                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True,
                            ).stdout.strip()
                            self.assertNotEqual(after_success, before)
                            self.assertEqual(json.loads(state_path.read_text())["committed_iscs"], ["ISC-1"])
                        finally:
                            bridge.close()
                finally:
                    os.chdir(previous_cwd)
            finally:
                subprocess.run(
                    ["git", "-C", str(source), "worktree", "remove", "--force", str(repo)],
                    check=True, capture_output=True, text=True,
                )
