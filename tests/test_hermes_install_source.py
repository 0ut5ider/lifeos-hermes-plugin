# ABOUTME: Checks Hermes source preparation against a disposable real Git repository.
# ABOUTME: Refuses altered source and staged candidates before any host apply action.

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.install_source import (
    IncompatibleLifeOS, apply_hermes_patch, prepare_hermes, stage_hermes_patch,
    recover_hermes_patch, request_hermes_restore, restore_hermes_patch, validate_hermes_candidate,
)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


class HermesSourceTests(unittest.TestCase):
    def fixture(self, root):
        source = root / "hermes"
        source.mkdir()
        git("init", "-q", "-b", "main", cwd=source)
        (source / "hermes_cli").mkdir()
        (source / ".gitignore").write_text(".hermes/\n")
        code = source / "hermes_cli/plugins.py"
        code.write_text("VALID_HOOKS = {'pre_tool_call'}\n")
        git("add", ".gitignore", "hermes_cli", cwd=source)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture", cwd=source)
        revision = git("rev-parse", "HEAD", cwd=source)
        code.write_text("VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n")
        added = source / "hermes_cli/new_hook.py"
        added.write_text("ENABLED = True\n")
        git("add", "-N", "hermes_cli/new_hook.py", cwd=source)
        patches = root / "patches"
        patches.mkdir()
        (patches / "host.patch").write_text(git("diff", "--", "hermes_cli", cwd=source) + "\n")
        git("reset", "-q", "--", "hermes_cli/new_hook.py", cwd=source)
        added.unlink()
        git("checkout", "--", "hermes_cli", cwd=source)
        return source, revision, patches

    def test_prepares_clean_exact_source_with_ordered_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            target = root / "candidate"
            manifest = prepare_hermes(source, target, revision, patches, ("host.patch",))
            self.assertEqual(manifest["base_commit"], revision)
            self.assertEqual(manifest["patches"][0]["name"], "host.patch")
            self.assertIn("pre_turn_stop", (target / "hermes_cli/plugins.py").read_text())
            self.assertEqual(validate_hermes_candidate(target, revision, patches,
                                                       ("host.patch",))["base_commit"], revision)
            (target / "hermes_cli/plugins.py").write_text("altered\n")
            with self.assertRaisesRegex(IncompatibleLifeOS, "changed"):
                validate_hermes_candidate(target, revision, patches, ("host.patch",))

    def test_refuses_modified_or_unsupported_running_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            (source / "untracked.txt").write_text("local")
            with self.assertRaisesRegex(IncompatibleLifeOS, "clean"):
                prepare_hermes(source, root / "candidate", revision, patches, ("host.patch",))
            (source / "untracked.txt").unlink()
            with self.assertRaisesRegex(IncompatibleLifeOS, "tested commit"):
                prepare_hermes(source, root / "candidate", "a" * 40, patches, ("host.patch",))
            self.assertFalse((root / "candidate").exists())

    def test_applies_patch_and_restores_after_failed_runtime_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_hermes(source, candidate, revision, patches, ("host.patch",))
            config = root / "config.yaml"
            config.write_text("model: local\n")
            snapshot = root / "snapshot"
            stage_hermes_patch(snapshot, source, candidate, config, revision,
                               patches, ("host.patch",))
            calls = []

            def fail_check():
                raise RuntimeError("gateway did not load")

            with self.assertRaisesRegex(IncompatibleLifeOS, "gateway did not load"):
                apply_hermes_patch(snapshot, stop=lambda: calls.append("stop"),
                                   start=lambda: calls.append("start"), verify=fail_check,
                                   verify_restored=lambda: calls.append("verified restore"))
            self.assertEqual(calls, ["stop", "start", "stop", "start", "verified restore"])
            self.assertNotIn("pre_turn_stop", (source / "hermes_cli/plugins.py").read_text())
            self.assertFalse((source / "hermes_cli/new_hook.py").exists())
            self.assertEqual(config.read_text(), "model: local\n")
            self.assertEqual(git("status", "--porcelain", cwd=source), "")

    def test_applies_prepared_patch_without_changing_ignored_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            runtime = source / ".hermes/bin/hermes"
            runtime.parent.mkdir(parents=True)
            runtime.write_text("runtime")
            candidate = root / "candidate"
            prepare_hermes(source, candidate, revision, patches, ("host.patch",))
            config = root / "config.yaml"
            config.write_text("model: local\n")
            snapshot = root / "snapshot"
            stage_hermes_patch(snapshot, source, candidate, config, revision,
                               patches, ("host.patch",))
            calls = []
            applied = apply_hermes_patch(snapshot, stop=lambda: calls.append("stop"),
                                         start=lambda: calls.append("start"),
                                         verify=lambda: calls.append("verify"))
            self.assertEqual(applied["state"], "applied")
            self.assertEqual(calls, ["stop", "start", "verify"])
            self.assertIn("pre_turn_stop", (source / "hermes_cli/plugins.py").read_text())
            self.assertEqual((source / "hermes_cli/new_hook.py").read_text(), "ENABLED = True\n")
            self.assertEqual(runtime.read_text(), "runtime")

    def interrupted(self, root, state):
        source, revision, patches = self.fixture(root)
        candidate = root / "candidate"
        prepare_hermes(source, candidate, revision, patches, ("host.patch",))
        config = root / "config.yaml"
        config.write_text("model: local\n")
        snapshot = root / "snapshot"
        stage_hermes_patch(snapshot, source, candidate, config, revision, patches, ("host.patch",))
        if state == "restoring":
            apply_hermes_patch(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)
            request_hermes_restore(snapshot)
        manifest = json.loads((snapshot / "manifest.json").read_text())
        manifest["state"] = state
        (snapshot / "manifest.json").write_text(json.dumps(manifest))
        # The killed worker wrote only one patched file before it died.
        (source / "hermes_cli/plugins.py").write_text("VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n")
        return source, snapshot

    def test_recovery_returns_an_interrupted_host_change_to_stock(self):
        for state in ("applying", "restoring"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                source, snapshot = self.interrupted(Path(directory), state)
                events = []
                result = recover_hermes_patch(snapshot, stop=lambda: events.append("stop"),
                                              start=lambda: events.append("start"),
                                              verify=lambda: events.append("verify"))
                self.assertEqual(result["state"], "rolled_back")
                self.assertEqual(git("status", "--porcelain", cwd=source), "")
                self.assertEqual(events, ["stop", "start", "verify"])
                self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "rolled_back")

    def test_recovery_refuses_a_finished_host_change(self):
        with tempfile.TemporaryDirectory() as directory:
            source, snapshot = self.interrupted(Path(directory), "restoring")
            manifest = json.loads((snapshot / "manifest.json").read_text())
            manifest["state"] = "applied"
            (snapshot / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(IncompatibleLifeOS, "interrupted"):
                recover_hermes_patch(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)

    def test_restore_preserves_later_hermes_config_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_hermes(source, candidate, revision, patches, ("host.patch",))
            config = root / "config.yaml"
            config.write_text("model: local\n")
            snapshot = root / "snapshot"
            stage_hermes_patch(snapshot, source, candidate, config, revision,
                               patches, ("host.patch",))
            apply_hermes_patch(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)
            config.write_text("model: other-local\n")
            result = restore_hermes_patch(snapshot, stop=lambda: None,
                                          start=lambda: None, verify=lambda: None)
            self.assertEqual(result["state"], "rolled_back")
            self.assertEqual(config.read_text(), "model: other-local\n")
            self.assertEqual(git("status", "--porcelain", cwd=source), "")

    def test_failed_restore_reapplies_the_prepared_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_hermes(source, candidate, revision, patches, ("host.patch",))
            config = root / "config.yaml"
            config.write_text("model: local\n")
            snapshot = root / "snapshot"
            stage_hermes_patch(snapshot, source, candidate, config, revision,
                               patches, ("host.patch",))
            apply_hermes_patch(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)
            checks = []

            def verify():
                checks.append("verify")
                if len(checks) == 1:
                    raise RuntimeError("stock gateway failed")

            with self.assertRaisesRegex(IncompatibleLifeOS, "stock gateway failed"):
                restore_hermes_patch(snapshot, stop=lambda: None, start=lambda: None, verify=verify)
            self.assertEqual(len(checks), 2)
            self.assertIn("pre_turn_stop", (source / "hermes_cli/plugins.py").read_text())
            self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "applied")

    def test_restore_request_prevents_duplicate_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_hermes(source, candidate, revision, patches, ("host.patch",))
            config = root / "config.yaml"
            config.write_text("model: local\n")
            snapshot = root / "snapshot"
            stage_hermes_patch(snapshot, source, candidate, config, revision,
                               patches, ("host.patch",))
            apply_hermes_patch(snapshot, stop=lambda: None, start=lambda: None, verify=lambda: None)
            request_hermes_restore(snapshot)
            with self.assertRaisesRegex(IncompatibleLifeOS, "already requested"):
                request_hermes_restore(snapshot)
            self.assertEqual(json.loads((snapshot / "manifest.json").read_text())["state"], "restoring")

    def test_start_failure_stops_gateway_before_restoring_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_hermes(source, candidate, revision, patches, ("host.patch",))
            config = root / "config.yaml"
            config.write_text("model: local\n")
            snapshot = root / "snapshot"
            stage_hermes_patch(snapshot, source, candidate, config, revision,
                               patches, ("host.patch",))
            calls = []

            def start():
                calls.append("start")
                if calls.count("start") == 1:
                    raise RuntimeError("start timed out")

            with self.assertRaisesRegex(IncompatibleLifeOS, "start timed out"):
                apply_hermes_patch(snapshot, stop=lambda: calls.append("stop"),
                                   start=start, verify=lambda: None)
            self.assertEqual(calls, ["stop", "start", "stop", "start"])
            self.assertEqual(git("status", "--porcelain", cwd=source), "")


if __name__ == "__main__":
    unittest.main()
