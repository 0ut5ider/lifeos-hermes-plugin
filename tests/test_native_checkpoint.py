# ABOUTME: Verifies LifeOS checkpoint commits against a disposable Git worktree.
# ABOUTME: Checks long project slugs and native checkpoint lookup through a real hook.

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


class NativeCheckpointTests(unittest.TestCase):
    def test_long_slug_checkpoint_remains_searchable(self):
        home = Path.home()
        source = home / "workspace/LifeOS"
        hook = home / ".claude/hooks/CheckpointPerISC.hook.ts"
        lookup = home / ".claude/LIFEOS/TOOLS/Checkpoint.ts"
        bun = home / ".bun/bin/bun"
        if not (source / ".git").exists() or not hook.exists() or not lookup.exists() or not bun.exists():
            self.skipTest("installed LifeOS checkout and Bun are required")

        with tempfile.TemporaryDirectory() as text:
            root = Path(text)
            repo = root / "repo"
            subprocess.run(
                ["git", "-C", str(source), "worktree", "add", "--detach", str(repo), "HEAD"],
                check=True, capture_output=True, text=True,
            )
            try:
                slug = "checkpoint-project-with-a-very-long-descriptive-slug-for-parity"
                session_home = root / "home"
                claude = session_home / ".claude"
                claude.mkdir(parents=True)
                isa = claude / "LIFEOS/MEMORY/WORK" / slug / "ISA.md"
                isa.parent.mkdir(parents=True)
                started = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
                isa.write_text(
                    f"---\ntitle: Long slug test\nstarted: {started}\n---\n\n"
                    "## Claims\n- [x] ISC-1: A completed claim\n"
                )
                (claude / "checkpoint-repos.txt").write_text(f"{repo}\n")
                (repo / "checkpoint-proof.txt").write_text("proof\n")
                before = subprocess.run(
                    ["git", "-C", str(repo), "rev-parse", "HEAD"],
                    check=True, capture_output=True, text=True,
                ).stdout.strip()
                environment = {
                    **os.environ,
                    "HOME": str(session_home),
                    "LIFEOS_DIR": str(claude / "LIFEOS"),
                    "GIT_AUTHOR_NAME": "Parity Probe",
                    "GIT_AUTHOR_EMAIL": "probe@example.invalid",
                    "GIT_COMMITTER_NAME": "Parity Probe",
                    "GIT_COMMITTER_EMAIL": "probe@example.invalid",
                }
                payload = {
                    "hook_event_name": "PostToolUse",
                    "session_id": "longslug-probe",
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(isa)},
                    "tool_response": "success",
                }
                process = subprocess.run(
                    [str(bun), str(hook)], input=json.dumps(payload), text=True,
                    capture_output=True, env=environment, timeout=15,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                after = subprocess.run(
                    ["git", "-C", str(repo), "rev-parse", "HEAD"],
                    check=True, capture_output=True, text=True,
                ).stdout.strip()
                self.assertNotEqual(after, before, process.stderr)
                state = json.loads((isa.parent / ".checkpoint-state.json").read_text())
                self.assertEqual(state["committed_iscs"], ["ISC-1"])
                message = subprocess.run(
                    ["git", "-C", str(repo), "show", "-s", "--format=%B", "HEAD"],
                    check=True, capture_output=True, text=True,
                ).stdout
                subject = message.splitlines()[0]
                self.assertLess(len(subject), 50)
                self.assertTrue(subject.startswith("chore(checkpoint): "))
                self.assertIn(f"ISC-1 ({slug}): A completed claim", message)
                found = subprocess.run(
                    [str(bun), str(lookup), "show", slug, "ISC-1"],
                    check=True, capture_output=True, text=True, env=environment, timeout=15,
                )
                self.assertIn(after, found.stdout)
            finally:
                subprocess.run(
                    ["git", "-C", str(source), "worktree", "remove", "--force", str(repo)],
                    check=True, capture_output=True, text=True,
                )
