# ABOUTME: Exercises a coordinated LifeOS update and rollback on disposable directories.
# ABOUTME: Verifies user data, Hermes mount files, and the baseline across failures.

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.native_capabilities import capability_record, supports_task_count, RECORD_NAME

from lifeos_hook_bridge.update_transaction import (
    UpdateTransactionError, apply_update, recover_update, restore_update,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UpdateTransactionTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("LIFEOS_TASK_HOOK_PATH"), "Prepared native TaskGovernance is required")
    def test_capability_record_applies_and_restores_with_native_hook_files(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            name = "hooks/TaskGovernance.hook.ts"
            for root in (installed, prior):
                (root / name).write_text("unpatched native hook")
            for root in (selected, reference):
                (root / name).write_bytes(Path(os.environ["LIFEOS_TASK_HOOK_PATH"]).read_bytes())
                (root / "hooks" / RECORD_NAME).write_text(json.dumps(capability_record()))
            data = json.loads(baseline.read_text())
            data["files"][name] = digest(installed / name)
            baseline.write_text(json.dumps(data))
            self.assertFalse(supports_task_count(installed))
            _, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            result = apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                                  stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual(result["state"], "applied")
            self.assertTrue(supports_task_count(installed))
            restored = restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(restored["state"], "rolled_back")
            self.assertFalse(supports_task_count(installed))
            self.assertFalse((installed / "hooks" / RECORD_NAME).exists())
            self.assertEqual((installed / name).read_text(), "unpatched native hook")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")

    def fixture(self, root):
        installed = root / "home/.claude"
        hermes = root / "home/.hermes"
        prior = root / "prior"
        selected = root / "selected"
        reference = root / "reference/.claude"
        baseline = root / "home/state/baseline.json"
        snapshot = root / "home/state/update"
        for path in (installed, hermes, prior, selected, reference):
            path.mkdir(parents=True)
        for path in (installed, prior, selected, reference):
            (path / "hooks").mkdir()
        (installed / "hooks/owned.ts").write_text("owned-v1")
        (installed / "LIFEOS/MEMORY").mkdir(parents=True)
        (installed / "LIFEOS/MEMORY/user.txt").write_text("private memory")
        (installed / "settings.json").write_text(json.dumps({"model": "private", "hooks": {
            "Stop": [{"matcher": "", "hooks": [
                {"type": "command", "command": "old.sh"},
                {"type": "command", "command": "foreign.sh"},
            ]}],
        }}))
        (installed / "package.json").write_text('{"version":"1"}')
        (installed / "bun.lock").write_text("old-lock")
        (installed / "node_modules").mkdir()
        (installed / "node_modules/library.txt").write_text("old-library")
        (prior / "hooks/owned.ts").write_text("owned-v1")
        (selected / "hooks/owned.ts").write_text("owned-v2")
        (reference / "hooks/owned.ts").write_text("owned-v2")
        (prior / "hooks/hooks.json").write_text(json.dumps({"hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "old.sh"}]}],
        }}))
        (selected / "hooks/hooks.json").write_text(json.dumps({"hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "new.sh"}]}],
        }}))
        (reference / "hooks/hooks.json").write_text((selected / "hooks/hooks.json").read_text())
        (prior / "package.json").write_text('{"version":"1"}')
        (selected / "package.json").write_text('{"version":"2"}')
        (reference / "package.json").write_text('{"version":"2"}')
        (reference / "bun.lock").write_text("new-lock")
        (reference / "node_modules").mkdir()
        (reference / "node_modules/library.txt").write_text("new-library")
        (hermes / "config.yaml").write_text("prior config")
        (hermes / "SOUL.md").write_text("prior soul")
        baseline.parent.mkdir(parents=True)
        baseline.write_text(json.dumps({"installed_root": str(installed.resolve()), "files": {
            "hooks/owned.ts": digest(installed / "hooks/owned.ts"),
        }}))
        return installed, hermes, prior, selected, reference, baseline, snapshot

    def callbacks(self, hermes, baseline, *, fail_verify=False):
        events = []

        def stop():
            events.append("stop")

        def start():
            events.append("start")

        def mount():
            (hermes / "config.yaml").write_text("selected config")
            (hermes / "SOUL.md").write_text("selected soul")

        def renew(installed, selected):
            baseline.write_text("selected baseline")

        def verify():
            events.append("verify")
            if fail_verify:
                raise RuntimeError("selected gateway failed")

        return events, stop, start, mount, renew, verify

    def test_applies_update_and_immediate_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            result = apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                                  stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual(result["state"], "applied")
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v2")
            self.assertEqual((installed / "node_modules/library.txt").read_text(), "new-library")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")
            self.assertEqual(json.loads((installed / "settings.json").read_text())["hooks"]["Stop"][0]
                             ["hooks"][0]["command"], "new.sh")
            self.assertEqual(baseline.read_text(), "selected baseline")
            self.assertEqual(events, ["stop", "start", "verify"])

            restored = restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
            self.assertEqual(restored["state"], "rolled_back")
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")
            self.assertEqual((hermes / "SOUL.md").read_text(), "prior soul")
            self.assertIn("installed_root", baseline.read_text())

    def test_verification_failure_restores_all_prior_state(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            before = baseline.read_bytes()
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline,
                                                                        fail_verify=True)
            with self.assertRaisesRegex(UpdateTransactionError, "selected gateway failed"):
                apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                             stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((installed / "node_modules/library.txt").read_text(), "old-library")
            self.assertEqual((installed / "LIFEOS/MEMORY/user.txt").read_text(), "private memory")
            self.assertEqual((hermes / "config.yaml").read_text(), "prior config")
            self.assertEqual(baseline.read_bytes(), before)
            self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "rolled_back")

    def test_second_directory_rename_failure_restores_installed_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            events, stop, start, mount, renew, verify = self.callbacks(hermes, baseline)
            original_replace = __import__("os").replace

            def fail_selected_swap(source, destination):
                if Path(source) == snapshot / "staged" and Path(destination) == installed:
                    raise OSError("selected swap failed")
                return original_replace(source, destination)

            with patch("lifeos_hook_bridge.update_transaction.os.replace", side_effect=fail_selected_swap):
                with self.assertRaisesRegex(UpdateTransactionError, "selected swap failed"):
                    apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                                 stop=stop, start=start, mount=mount, renew=renew, verify=verify)
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((hermes / "config.yaml").read_text(), "prior config")
            self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "rolled_back")

    def test_recovers_process_death_between_directory_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            installed, hermes, prior, selected, reference, baseline, snapshot = self.fixture(Path(directory))
            snapshot.mkdir()
            (snapshot / "mount").mkdir()
            (snapshot / "mount/config.yaml").write_text("prior config")
            (snapshot / "mount/SOUL.md").write_text("prior soul")
            (snapshot / "baseline.json").write_bytes(baseline.read_bytes())
            (snapshot / "mount-manifest.json").write_text(json.dumps({"present": ["config.yaml", "SOUL.md"]}))
            (snapshot / "manifest.json").write_text(json.dumps({
                "state": "stopped", "installed": str(installed), "hermes_home": str(hermes),
                "baseline": str(baseline),
            }))
            installed.rename(snapshot / "live-prior")
            (hermes / "config.yaml").write_text("interrupted mount")
            baseline.write_text("interrupted baseline")
            events = []
            result = recover_update(snapshot, stop=lambda: events.append("stop"),
                                    start=lambda: events.append("start"),
                                    verify=lambda: events.append("verify"))
            self.assertEqual(result["state"], "rolled_back")
            self.assertEqual((installed / "hooks/owned.ts").read_text(), "owned-v1")
            self.assertEqual((hermes / "config.yaml").read_text(), "prior config")
            self.assertIn("installed_root", baseline.read_text())
            self.assertEqual(events, ["stop", "start", "verify"])
