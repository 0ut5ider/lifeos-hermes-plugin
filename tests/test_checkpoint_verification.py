# ABOUTME: Runs native checkpoint verification in disposable repositories.
# ABOUTME: Checks slow checks, rejection retries, and verifier process cleanup.

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


HOOK_PATH = os.environ.get("LIFEOS_CHECKPOINT_HOOK_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS checkpoint hook and Bun are required")
class CheckpointVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "--quiet")
        self.home = self.root / "home"
        claude = self.home / ".claude"
        claude.mkdir(parents=True)
        self.isa = claude / "LIFEOS/MEMORY/WORK/verification/ISA.md"
        self.isa.parent.mkdir(parents=True)
        started = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.isa.write_text(f"---\ntitle: Verification\nstarted: {started}\n---\n\n## Claims\n- [x] ISC-1: Verified checkpoint\n")
        (claude / "checkpoint-repos.txt").write_text(f"{self.repo}\n")
        (self.repo / "proof.txt").write_text("proof\n")
        self.environment = {
            **os.environ, "HOME": str(self.home), "LIFEOS_DIR": str(claude / "LIFEOS"),
            "GIT_AUTHOR_NAME": "Checkpoint Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Checkpoint Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        self.check = self.repo / ".git/hooks/pre-commit"

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], text=True, capture_output=True, check=True).stdout

    def install_check(self, text):
        self.check.write_text("#!/bin/sh\n" + text)
        self.check.chmod(0o755)

    def invoke(self):
        process = subprocess.run(
            ["bun", HOOK_PATH], input=json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str(self.isa)}}), text=True, capture_output=True,
            env=self.environment, timeout=28,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), {"continue": True})
        return process, json.loads((self.isa.parent / ".checkpoint-state.json").read_text())

    def test_check_longer_than_five_seconds_commits(self):
        self.install_check("sleep 6\n")
        process, state = self.invoke()
        self.assertEqual(process.stderr, "")
        self.assertEqual(state["committed_iscs"], ["ISC-1"])
        self.assertEqual(self.git("show", "HEAD:proof.txt"), "proof\n")

    def test_rejected_check_stays_pending_and_retry_commits(self):
        self.install_check("echo expected-rejection >&2\nexit 1\n")
        process, state = self.invoke()
        self.assertIn("expected-rejection", process.stderr)
        self.assertEqual(state["committed_iscs"], [])
        self.install_check("exit 0\n")
        process, state = self.invoke()
        self.assertEqual(process.stderr, "")
        self.assertEqual(state["committed_iscs"], ["ISC-1"])

    def test_timeout_stops_verifier_children_and_allows_retry(self):
        self.environment["LIFEOS_CHECKPOINT_COMMIT_TIMEOUT_MS"] = "500"
        pid = self.root / "child.pid"
        marker = self.root / "unexpected-completion"
        self.install_check(f"(sleep 3; touch '{marker}') &\necho $! > '{pid}'\nwait\n")
        started = time.monotonic()
        process, state = self.invoke()
        self.assertLess(time.monotonic() - started, 3)
        self.assertIn("verification timed out", process.stderr)
        self.assertEqual(state["committed_iscs"], [])
        self.assertTrue(pid.exists())
        status = Path(f"/proc/{pid.read_text().strip()}/status")
        if status.exists():
            self.assertIn("State:\tZ", status.read_text(), "Verifier child survived timeout")
        self.assertFalse(marker.exists())
        self.assertFalse((self.repo / ".git/index.lock").exists())
        self.install_check("exit 0\n")
        _, state = self.invoke()
        self.assertEqual(state["committed_iscs"], ["ISC-1"])
