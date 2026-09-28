# ABOUTME: Checks the native LifeOS version hook on an untagged installation.
# ABOUTME: Runs VersionDrift through Hermes in a disposable home with no Git tags.

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


HOOK_PATH = os.environ.get("LIFEOS_VERSION_DRIFT_PATH")
TAGGED_REPO_PATH = os.environ.get("LIFEOS_VERSION_DRIFT_TAGGED_REPO_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS VersionDrift and Bun are required")
class NativeVersionDriftTests(unittest.TestCase):
    @unittest.skipUnless(TAGGED_REPO_PATH, "a tagged read-only Git repository is required")
    def test_drift_nag_reaches_prompt_once(self):
        repo = Path(TAGGED_REPO_PATH)
        tags = subprocess.check_output(
            ["git", "-C", str(repo), "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"],
            text=True,
        ).splitlines()
        if not tags:
            self.skipTest("the read-only Git repository has no semantic version tag")
        git_dir = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"], text=True,
        ).strip()

        with tempfile.TemporaryDirectory(prefix="lifeos-version-drift-active-") as directory:
            home = Path(directory)
            root = home / ".claude"
            (root / "LIFEOS").mkdir(parents=True)
            (root / "LIFEOS/VERSION").write_text(tags[0][1:] + "\n")
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(HOME=str(home), GIT_DIR=git_dir, GIT_WORK_TREE=str(root))
            try:
                first = bridge.pre_llm_call("Check the release", session_id="version-probe")
                second = bridge.pre_llm_call("Check the release again", session_id="version-probe")
            finally:
                bridge.close()

            self.assertIn("VERSION-DRIFT", first["context"])
            self.assertIn(tags[0], first["context"])
            self.assertIsNone(second)
            state = json.loads((root / "LIFEOS/MEMORY/STATE/version-drift-nag.json").read_text())
            self.assertEqual(state["tag"], tags[0])
            self.assertGreaterEqual(state["count"], 10)

    def test_untagged_installation_does_not_nag(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-version-drift-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["HOME"] = str(home)
            try:
                result = bridge.pre_llm_call("Check the release", session_id="version-probe")
            finally:
                bridge.close()

            self.assertIsNone(result)
            self.assertFalse((root / "LIFEOS/MEMORY/STATE/version-drift-nag.json").exists())
