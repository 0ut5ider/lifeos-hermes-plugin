# ABOUTME: Checks that LifeOS does not route private prompts without a work repo.
# ABOUTME: Runs the installed ReminderRouter through Hermes with a fake gh command.

import json
import os
import shutil
import time
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from shlex import quote

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_REMINDER_ROUTER_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS ReminderRouter and Bun are required")
class NativeReminderRouterTests(unittest.TestCase):
    def test_verified_private_repo_routes_to_fake_gh(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-reminder-enabled-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            lifeos = root / "LIFEOS"
            work = lifeos / "USER/WORK"
            work.mkdir(parents=True)
            (work / "work_repo.json").write_text(json.dumps({
                "repo": "test-owner/private-work",
                "privacy": {
                    "verified_private": True,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "visibility": "PRIVATE",
                },
            }))
            marker = home / "gh-args"
            fake_bin = home / "bin"
            fake_bin.mkdir()
            gh = fake_bin / "gh"
            gh.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {quote(str(marker))}\n")
            gh.chmod(0o755)
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(
                HOME=str(home), LIFEOS_DIR=str(lifeos), PATH=f"{fake_bin}:{bridge.environment['PATH']}",
            )
            prompt = "Remind me to review the draft tomorrow"
            try:
                result = bridge.pre_llm_call(prompt, session_id="reminder-enabled")
            finally:
                bridge.close()
            deadline = time.monotonic() + 3
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)

            self.assertIsNone(result)
            args = marker.read_text().splitlines()
            self.assertEqual(args[:4], ["issue", "create", "--repo", "test-owner/private-work"])
            self.assertIn(prompt, args)
            self.assertTrue((lifeos / "MEMORY/STATE/reminder-router-seen.json").exists())

    def test_matching_prompt_stays_local_without_work_repo(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-reminder-router-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            lifeos = root / "LIFEOS"
            lifeos.mkdir()
            marker = home / "gh-called"
            fake_bin = home / "bin"
            fake_bin.mkdir()
            gh = fake_bin / "gh"
            gh.write_text(f"#!/bin/sh\nprintf called > {marker}\n")
            gh.chmod(0o755)
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(
                HOME=str(home), LIFEOS_DIR=str(lifeos), PATH=f"{fake_bin}:{bridge.environment['PATH']}",
            )
            try:
                result = bridge.pre_llm_call("Remind me to review the draft tomorrow", session_id="reminder-probe")
            finally:
                bridge.close()

            self.assertIsNone(result)
            self.assertFalse(marker.exists())
            self.assertFalse((lifeos / "MEMORY/STATE/reminder-router-seen.json").exists())
