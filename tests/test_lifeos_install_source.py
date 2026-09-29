# ABOUTME: Checks LifeOS source preparation against an actual disposable Git repository.
# ABOUTME: Keeps failed or unsupported revisions out of the install candidate directory.

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge.install_source import (
    INSTALL_STEPS, IncompatibleLifeOS, finalize_lifeos, install_lifeos, prepare_lifeos, validate_candidate,
)
from lifeos_hook_bridge.version_drift import create_baseline, save_baseline


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=True).stdout.strip()


class InstallSourceTests(unittest.TestCase):
    def fixture(self, root):
        upstream = root / "upstream"
        upstream.mkdir()
        git("init", "-q", "-b", "main", cwd=upstream)
        version = upstream / "LifeOS/install/LIFEOS/VERSION"
        version.parent.mkdir(parents=True)
        version.write_text("7.40.4\n")
        (upstream / "LifeOS/install/CLAUDE.template.md").write_text("# LifeOS test\n")
        checked = upstream / "LifeOS/install/LIFEOS/TOOLS/Check.ts"
        checked.parent.mkdir(parents=True)
        checked.write_text("export const checked = true;\n")
        tools = upstream / "LifeOS/Tools"
        tools.mkdir(parents=True)
        (tools / "InstallSettings.ts").write_text(
            'const a = process.argv; const r = a[a.indexOf("--config-root") + 1];'
            'await Bun.write(r + "/started", "ran"); process.exit(23);\n'
        )
        for name in INSTALL_STEPS[1:]:
            (tools / f"{name}.ts").write_text('console.log("unused in failure probe");\n')
        git("add", "LifeOS", cwd=upstream)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture", cwd=upstream)
        revision = git("rev-parse", "HEAD", cwd=upstream)
        version.write_text("7.40.5\n")
        patches = root / "patches"
        patches.mkdir()
        (patches / "lifeos-test.patch").write_text(git("diff", "--", "LifeOS", cwd=upstream) + "\n")
        git("checkout", "--", "LifeOS", cwd=upstream)
        return upstream, revision, patches

    def test_prepares_exact_upstream_revision_and_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            target = root / "candidate"
            manifest = prepare_lifeos(str(upstream), target, revision, patches,
                                      ("lifeos-test.patch",))
            self.assertEqual((target / "LifeOS/install/LIFEOS/VERSION").read_text(), "7.40.5\n")
            self.assertEqual(manifest["upstream_commit"], revision)
            self.assertEqual(manifest["patches"][0]["name"], "lifeos-test.patch")
            self.assertEqual(json.loads((target / "lifeos-source-manifest.json").read_text()), manifest)
            self.assertEqual(git("rev-parse", "HEAD", cwd=target), revision)

    def test_dashboard_standalone_module_prepares_source(self):
        module_path = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/install_source.py"
        spec = importlib.util.spec_from_file_location("lifeos_install_source", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertFalse(module.__package__)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            target = root / "candidate"
            manifest = module.prepare_lifeos(str(upstream), target, revision, patches, ("lifeos-test.patch",))
            self.assertEqual(manifest["upstream_commit"], revision)
            self.assertEqual(module.validate_candidate(target, revision, patches, ("lifeos-test.patch",)), manifest)

    def test_new_upstream_revision_is_not_silently_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, supported, patches = self.fixture(root)
            (upstream / "LifeOS/install/LIFEOS/VERSION").write_text("7.40.5\n")
            git("add", "LifeOS", cwd=upstream)
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-qm", "later", cwd=upstream)
            target = root / "candidate"
            with self.assertRaises(IncompatibleLifeOS):
                prepare_lifeos(str(upstream), target, supported, patches,
                               ("lifeos-test.patch",))
            self.assertFalse(target.exists())

    def test_failed_patch_leaves_no_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            (patches / "lifeos-test.patch").write_text("invalid patch\n")
            target = root / "candidate"
            with self.assertRaises(IncompatibleLifeOS):
                prepare_lifeos(str(upstream), target, revision, patches,
                               ("lifeos-test.patch",))
            self.assertFalse(target.exists())

    def test_candidate_change_is_detected_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            target = root / "candidate"
            prepare_lifeos(str(upstream), target, revision, patches,
                           ("lifeos-test.patch",))
            self.assertEqual(validate_candidate(target, revision, patches,
                                                ("lifeos-test.patch",))["upstream_commit"], revision)
            (target / "LifeOS/install/LIFEOS/VERSION").write_text("changed after preparation\n")
            with self.assertRaisesRegex(IncompatibleLifeOS, "changed"):
                validate_candidate(target, revision, patches, ("lifeos-test.patch",))

    def test_failed_fresh_install_preserves_partial_files_for_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_lifeos(str(upstream), candidate, revision, patches,
                           ("lifeos-test.patch",))
            installed = root / "home/.claude"
            failed = root / "failed-install"
            with self.assertRaisesRegex(IncompatibleLifeOS, "InstallSettings"):
                install_lifeos(candidate, installed, failed, "bun", revision, patches,
                               ("lifeos-test.patch",))
            self.assertFalse(installed.exists())
            self.assertEqual((failed / "CLAUDE.md").read_text(), "# LifeOS test\n")
            self.assertEqual((failed / "started").read_text(), "ran")

    def test_fresh_install_places_selected_bun_on_child_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_lifeos(str(upstream), candidate, revision, patches,
                           ("lifeos-test.patch",))
            binary = root / "private-bin/bun"
            binary.parent.mkdir()
            binary.write_text('#!/bin/sh\ncommand -v bun >/dev/null && printf yes > "$BUN_PROBE_FILE" || printf no > "$BUN_PROBE_FILE"\nexit 23\n')
            binary.chmod(0o755)
            marker = root / "path-marker"
            with patch.dict("os.environ", {"PATH": "/usr/bin:/bin", "BUN_PROBE_FILE": str(marker)}):
                with self.assertRaisesRegex(IncompatibleLifeOS, "InstallSettings"):
                    install_lifeos(candidate, root / "home/.claude", root / "failed", str(binary),
                                   revision, patches, ("lifeos-test.patch",))
            self.assertEqual(marker.read_text(), "yes")

    def test_fresh_install_refuses_existing_claude_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_lifeos(str(upstream), candidate, revision, patches,
                           ("lifeos-test.patch",))
            installed = root / "home/.claude"
            installed.mkdir(parents=True)
            (installed / "keep.txt").write_text("private")
            with self.assertRaisesRegex(IncompatibleLifeOS, "already exists"):
                install_lifeos(candidate, installed, root / "failed", "bun", revision, patches,
                               ("lifeos-test.patch",))
            self.assertEqual((installed / "keep.txt").read_text(), "private")

    def test_finalization_mounts_and_records_installed_system_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_lifeos(str(upstream), candidate, revision, patches,
                           ("lifeos-test.patch",))
            installed = root / "home/.claude"
            hermes_home = root / "home/.hermes"
            (installed / "LIFEOS/HERMES").mkdir(parents=True)
            (installed / "LIFEOS/VERSION").write_text("7.40.5\n")
            (installed / "LIFEOS/TOOLS").mkdir()
            (installed / "LIFEOS/TOOLS/Check.ts").write_text("export const checked = true;\n")
            (installed / "settings.json").write_text('{"hooks": {"Stop": [{}]}}')
            (installed / "LIFEOS/HERMES/Mount.ts").write_text("fixture")
            hermes_home.mkdir()
            (hermes_home / "config.yaml").write_text("model:\n  default: local\n")
            bun = root / "bun"
            bun.write_text("#!/bin/sh\nif [ \"$2\" = '--check' ]; then exit 0; fi\n"
                           "printf 'mounted\\n' > \"$HERMES_HOME/SOUL.md\"\n")
            bun.chmod(0o755)
            hermes = root / "hermes"
            hermes.write_text("#!/bin/sh\ntest \"$1 $2\" = 'config check'\n")
            hermes.chmod(0o755)
            baseline = root / "home/.local/state/lifeos-bridge/baseline.json"
            result = finalize_lifeos(candidate, installed, hermes_home, baseline,
                                     str(bun), str(hermes), revision, patches,
                                     ("lifeos-test.patch",), create_baseline, save_baseline)
            self.assertTrue(result["restart_required"])
            self.assertEqual((hermes_home / "SOUL.md").read_text(), "mounted\n")
            self.assertEqual(json.loads(baseline.read_text())["version"], "7.40.5")

    def test_failed_mount_restores_hermes_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream, revision, patches = self.fixture(root)
            candidate = root / "candidate"
            prepare_lifeos(str(upstream), candidate, revision, patches,
                           ("lifeos-test.patch",))
            installed = root / "home/.claude"
            (installed / "LIFEOS/HERMES").mkdir(parents=True)
            (installed / "LIFEOS/VERSION").write_text("7.40.5\n")
            (installed / "settings.json").write_text('{"hooks": {"Stop": [{}]}}')
            (installed / "LIFEOS/HERMES/Mount.ts").write_text("fixture")
            hermes_home = root / "home/.hermes"
            hermes_home.mkdir()
            (hermes_home / "config.yaml").write_text("model:\n  default: local\n")
            (hermes_home / "SOUL.md").write_text("previous soul\n")
            bun = root / "bun"
            bun.write_text("#!/bin/sh\nprintf 'partial\\n' > \"$HERMES_HOME/SOUL.md\"\n"
                           "printf 'changed\\n' > \"$HERMES_HOME/config.yaml\"\nexit 17\n")
            bun.chmod(0o755)
            hermes = root / "hermes"
            hermes.write_text("#!/bin/sh\nexit 0\n")
            hermes.chmod(0o755)
            baseline = root / "home/.local/state/lifeos-bridge/baseline.json"
            with self.assertRaisesRegex(IncompatibleLifeOS, "Mount"):
                finalize_lifeos(candidate, installed, hermes_home, baseline,
                                str(bun), str(hermes), revision, patches,
                                ("lifeos-test.patch",), create_baseline, save_baseline)
            self.assertEqual((hermes_home / "SOUL.md").read_text(), "previous soul\n")
            self.assertEqual((hermes_home / "config.yaml").read_text(), "model:\n  default: local\n")
            self.assertFalse(baseline.exists())


if __name__ == "__main__":
    unittest.main()
