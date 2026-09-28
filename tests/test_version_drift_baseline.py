# ABOUTME: Verifies a plugin-owned LifeOS version baseline and its scoped Git adapter.
# ABOUTME: Uses a disposable source repository and deployed tree without Git metadata.

import hashlib
import json
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge.version_drift import (
    adapter_error_path, baseline_fingerprint, create_baseline, changed_paths, default_baseline_path,
    git_response, load_baseline, save_baseline,
)


class VersionDriftBaselineTests(unittest.TestCase):
    def test_default_baseline_is_outside_hermes_and_config_roots(self):
        self.assertEqual(default_baseline_path(),
                         Path.home() / ".local/state/lifeos-hook-bridge/version-drift-baseline.json")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.installed = self.root / "home" / ".claude"
        self.source.mkdir()
        self.installed.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        (self.source / "LIFEOS").mkdir()
        (self.installed / "LIFEOS").mkdir()
        (self.source / "LIFEOS/VERSION").write_text("7.40.4\n")
        (self.installed / "LIFEOS/VERSION").write_text("7.40.4\n")
        self._file("hooks/VersionDrift.hook.ts", "native hook")
        self._file("LIFEOS/TOOLS/Check.ts", "baseline")
        self._file("skills/research/SKILL.md", "skill")
        self._file("LIFEOS/PULSE/node_modules/private.json", "dependency secret")
        subprocess.run(["git", "-C", str(self.source), "add", "LIFEOS/VERSION", "hooks", "LIFEOS/TOOLS", "skills"], check=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)

    def _file(self, name, content):
        for root in (self.source, self.installed):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def test_baseline_uses_tracked_installed_system_files_only(self):
        baseline = create_baseline(self.source, self.installed)
        self.assertEqual(baseline["version"], "7.40.4")
        self.assertEqual(len(baseline["source_commit"]), 40)
        self.assertEqual(baseline["files"]["LIFEOS/TOOLS/Check.ts"], hashlib.sha256(b"baseline").hexdigest())
        self.assertNotIn("LIFEOS/PULSE/node_modules/private.json", baseline["files"])
        self.assertNotIn("LIFEOS/VERSION", baseline["files"])
        self.assertEqual(set(baseline["files"]), {
            "hooks/VersionDrift.hook.ts", "LIFEOS/TOOLS/Check.ts", "skills/research/SKILL.md",
        })

    def test_changed_paths_include_edits_deletes_and_new_system_files(self):
        baseline = create_baseline(self.source, self.installed)
        (self.installed / "LIFEOS/TOOLS/Check.ts").write_text("changed")
        (self.installed / "hooks/VersionDrift.hook.ts").unlink()
        (self.installed / "LIFEOS/TOOLS/New.ts").write_text("new")
        (self.installed / "LIFEOS/TOOLS/.env").write_text("secret")
        (self.installed / "skills/research/new.md").write_text("new owned skill file")
        (self.installed / "skills/other").mkdir()
        (self.installed / "skills/other/SKILL.md").write_text("unrelated Hermes skill")
        changed = changed_paths(baseline, self.installed)
        self.assertEqual(changed, [
            "LIFEOS/TOOLS/Check.ts", "LIFEOS/TOOLS/New.ts", "hooks/VersionDrift.hook.ts",
            "skills/research/new.md",
        ])

    def test_adapter_answers_only_native_read_only_queries(self):
        baseline = create_baseline(self.source, self.installed)
        self.assertEqual(git_response(baseline, self.installed, ["tag", "-l", "v[0-9]*.[0-9]*.[0-9]*"]), "v7.40.4\n")
        self.assertEqual(git_response(baseline, self.installed, ["log", "-1", "--format=%ct", "v7.40.4"]),
                         f"{baseline['created_at']}\n")
        self.assertEqual(git_response(baseline, self.installed, ["diff", "--name-only", "v7.40.4", "--", "hooks/"]), "")
        with self.assertRaises(ValueError):
            git_response(baseline, self.installed, ["tag", "v7.40.5"])

    def test_baseline_write_is_private_and_requires_explicit_renewal(self):
        baseline = create_baseline(self.source, self.installed)
        destination = self.root / "config" / "baseline.json"
        save_baseline(baseline, destination)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(destination.read_text()), baseline)
        with self.assertRaises(FileExistsError):
            save_baseline(baseline, destination)
        save_baseline(baseline, destination, renew=True)

    def test_baseline_rejects_mismatched_source_version(self):
        (self.source / "LIFEOS/VERSION").write_text("7.40.5\n")
        with self.assertRaises(ValueError):
            create_baseline(self.source, self.installed)

    def test_review_fingerprint_changes_with_installed_content(self):
        first = create_baseline(self.source, self.installed)
        (self.installed / "LIFEOS/TOOLS/Check.ts").write_text("changed before approval")
        second = create_baseline(self.source, self.installed)
        self.assertNotEqual(baseline_fingerprint(first), baseline_fingerprint(second))

    def test_executable_adapter_delegates_other_git_calls(self):
        baseline = create_baseline(self.source, self.installed)
        destination = self.root / "baseline.json"
        save_baseline(baseline, destination)
        adapter = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/bin/git"
        environment = {
            "PATH": os.environ["PATH"],
            "LIFEOS_VERSION_DRIFT_BASELINE": str(destination),
            "LIFEOS_VERSION_DRIFT_ROOT": str(self.installed),
            "LIFEOS_VERSION_DRIFT_SYSTEM_GIT": shutil.which("git"),
        }
        tag = subprocess.run([str(adapter), "-C", str(self.installed), "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*"],
                             env=environment, capture_output=True, text=True, check=True)
        self.assertEqual(tag.stdout, "v7.40.4\n")
        system = subprocess.run([str(adapter), "--version"], env=environment,
                                capture_output=True, text=True, check=True)
        self.assertTrue(system.stdout.startswith("git version "))
        destination.unlink()
        missing = subprocess.run([str(adapter), "-C", str(self.installed), "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*"],
                                 env=environment, capture_output=True, text=True, check=False)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stdout, "")
        self.assertIn("baseline unavailable", missing.stderr)
        diagnostic = adapter_error_path(destination)
        self.assertEqual(diagnostic.stat().st_mode & 0o777, 0o600)
        self.assertIn("baseline.json", json.loads(diagnostic.read_text())["message"])

    def test_loaded_baseline_rejects_path_traversal(self):
        baseline = create_baseline(self.source, self.installed)
        baseline["files"]["hooks/../USER/private.json"] = "0" * 64
        destination = self.root / "baseline.json"
        save_baseline(baseline, destination)
        with self.assertRaises(ValueError):
            load_baseline(destination, self.installed)

    def test_scripts_run_from_installed_hyphenated_plugin_directory(self):
        source_runtime = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge"
        installed_runtime = self.root / "lifeos-hook-bridge"
        shutil.copytree(source_runtime, installed_runtime, ignore=shutil.ignore_patterns("__pycache__"))
        baseline = create_baseline(self.source, self.installed)
        destination = self.root / "baseline.json"
        save_baseline(baseline, destination)
        environment = dict(os.environ,
                           LIFEOS_VERSION_DRIFT_BASELINE=str(destination),
                           LIFEOS_VERSION_DRIFT_ROOT=str(self.installed),
                           LIFEOS_VERSION_DRIFT_SYSTEM_GIT=shutil.which("git"))
        adapter = subprocess.run([
            str(installed_runtime / "bin/git"), "-C", str(self.installed),
            "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*",
        ], env=environment, capture_output=True, text=True)
        self.assertEqual(adapter.returncode, 0, adapter.stderr)
        self.assertEqual(adapter.stdout, "v7.40.4\n")
        preview = subprocess.run([
            str(installed_runtime / "bin/version-drift-baseline"),
            "--source", str(self.source), "--installed", str(self.installed),
            "--baseline", str(self.root / "another.json"),
        ], env=environment, capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(json.loads(preview.stdout)["file_count"], 3)


if __name__ == "__main__":
    unittest.main()
