# ABOUTME: Checks the read-only Hermes compatibility detector against disposable real Git installations.
# ABOUTME: Covers supported, unsupported, edited, partially patched, shared, and unsupported-layout hosts.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from optional.lifeos_release_manager.host_compatibility import inspect_host, load_manifest, ManifestRejected


STOCK_PLUGINS = "VALID_HOOKS = {'pre_tool_call'}\n"
PATCHED_PLUGINS = "VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n"
ADDED_HOOK = "ENABLED = True\n"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def snapshot(root):
    """Record every file and directory identity below root, including Git metadata."""
    state = {}
    for directory, names, files in os.walk(root):
        for name in (*names, *files):
            path = Path(directory) / name
            info = path.lstat()
            content = path.read_bytes() if path.is_file() and not path.is_symlink() else b""
            state[path.relative_to(root).as_posix()] = (info.st_mode, info.st_mtime_ns, info.st_size,
                hashlib.sha256(content).hexdigest())
    return state


class HostCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.home = self.root / ".hermes"
        self.home.mkdir(mode=0o700)
        self.source = self.root / "hermes-agent"
        self.source.mkdir(mode=0o755)
        self.source.chmod(0o755)
        git("init", "-q", "-b", "main", cwd=self.source)
        (self.source / "hermes_cli").mkdir()
        (self.source / "hermes_cli/__init__.py").write_text("")
        (self.source / "hermes_cli/plugins.py").write_text(STOCK_PLUGINS)
        (self.source / "model_tools.py").write_text("TOOLS = []\n")
        (self.source / "run_agent.py").write_text("")
        (self.source / "pyproject.toml").write_text("[project]\nname = 'hermes-agent'\n")
        (self.source / ".gitignore").write_text("venv/\n")
        git("add", ".", cwd=self.source)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base", cwd=self.source)
        git("tag", "v0.0.1", cwd=self.source)
        self.commit = git("rev-parse", "HEAD", cwd=self.source)
        self.manifest = {
            "format": 1,
            "hermes": [{
                "label": "v0.0.1",
                "commit": self.commit,
                "patches": [{"name": "host.patch", "sha256": "e" * 64}],
                "files": {
                    "hermes_cli/plugins.py": {"stock": digest(STOCK_PLUGINS), "patched": digest(PATCHED_PLUGINS)},
                    "hermes_cli/new_hook.py": {"stock": None, "patched": digest(ADDED_HOOK)},
                },
            }],
            "dependencies": [{"name": "tree-sitter", "version": "0.26.0"}],
        }
        self.packages = self.root / "site-packages"
        self.packages.mkdir()

    def inspect(self, **options):
        return inspect_host(self.source, load_manifest(self.manifest), hermes_home=self.home,
                            search_path=[str(self.packages)], **options)

    def codes(self, result):
        return [reason["code"] for reason in result["reasons"]]

    def install_package(self, name, version):
        info = self.packages / f"{name.replace('-', '_')}-{version}.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")

    def patch(self, *, plugins=True, added=True):
        if plugins:
            (self.source / "hermes_cli/plugins.py").write_text(PATCHED_PLUGINS)
        if added:
            (self.source / "hermes_cli/new_hook.py").write_text(ADDED_HOOK)

    def test_exact_qualified_clean_installation_is_compatible(self):
        result = self.inspect()
        self.assertEqual(result["state"], "compatible")
        self.assertTrue(result["compatible"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["detected"]["commit"], self.commit)
        self.assertEqual(result["detected"]["source"], str(self.source))
        self.assertEqual(result["detected"]["version"], "v0.0.1")
        self.assertEqual(result["qualified"], "v0.0.1")
        self.assertEqual(result["dependencies"], {"add": ["tree-sitter==0.26.0"], "conflicts": []})
        self.assertEqual(result["supported"], [{"label": "v0.0.1", "commit": self.commit}])

    def test_inspection_changes_no_source_or_git_file(self):
        (self.source / "model_tools.py").write_text("TOOLS = ['edited']\n")
        before = snapshot(self.source)
        self.inspect()
        self.assertEqual(snapshot(self.source), before)

    def test_unknown_commit_reports_detected_and_supported_versions(self):
        (self.source / "model_tools.py").write_text("TOOLS = ['newer']\n")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qam", "newer",
            cwd=self.source)
        result = self.inspect()
        self.assertEqual(result["state"], "unsupported_version")
        self.assertFalse(result["compatible"])
        self.assertEqual(self.codes(result), ["unsupported_version"])
        self.assertTrue(result["detected"]["version"].startswith("v0.0.1-1-g"))
        self.assertIsNone(result["qualified"])
        self.assertEqual(result["supported"][0]["commit"], self.commit)

    def test_edit_outside_patch_targets_is_refused_with_its_path(self):
        (self.source / "model_tools.py").write_text("TOOLS = ['edited']\n")
        result = self.inspect()
        self.assertEqual(result["state"], "modified_source")
        self.assertEqual(result["reasons"][0]["paths"], ["model_tools.py"])

    def test_edit_inside_patch_target_is_refused_by_file_hash(self):
        (self.source / "hermes_cli/plugins.py").write_text(STOCK_PLUGINS + "# local\n")
        result = self.inspect()
        self.assertEqual(result["state"], "modified_source")
        self.assertEqual(result["reasons"][0]["paths"], ["hermes_cli/plugins.py"])

    def test_untracked_source_file_is_refused(self):
        (self.source / "hermes_cli/extra.py").write_text("")
        result = self.inspect()
        self.assertEqual(result["state"], "modified_source")
        self.assertEqual(result["reasons"][0]["code"], "untracked_files")
        self.assertEqual(result["reasons"][0]["paths"], ["hermes_cli/extra.py"])

    def test_ignored_files_do_not_block_installation(self):
        (self.source / "venv").mkdir()
        (self.source / "venv/pyvenv.cfg").write_text("home = /usr\n")
        self.assertEqual(self.inspect()["state"], "compatible")

    def test_change_hidden_from_git_status_is_refused(self):
        git("update-index", "--skip-worktree", "model_tools.py", cwd=self.source)
        (self.source / "model_tools.py").write_text("TOOLS = ['hidden']\n")
        result = self.inspect()
        self.assertEqual(result["state"], "modified_source")
        self.assertIn("hidden_changes", self.codes(result))

    def test_partially_patched_installation_is_refused(self):
        self.patch(added=False)
        result = self.inspect()
        self.assertEqual(result["state"], "partially_patched")
        self.assertEqual(result["reasons"][0]["paths"], ["hermes_cli/plugins.py"])

    def test_added_target_already_present_is_partial(self):
        self.patch(plugins=False)
        result = self.inspect()
        self.assertEqual(result["state"], "partially_patched")
        self.assertEqual(result["reasons"][0]["paths"], ["hermes_cli/new_hook.py"])

    def test_fully_patched_installation_without_record_is_refused(self):
        self.patch()
        result = self.inspect()
        self.assertEqual(result["state"], "patched_without_record")
        self.assertEqual(self.codes(result), ["patched_without_record"])

    def test_symbolic_link_at_patch_target_is_modified_source(self):
        (self.source / "hermes_cli/plugins.py").unlink()
        (self.source / "hermes_cli/plugins.py").symlink_to(self.source / "model_tools.py")
        result = self.inspect()
        self.assertEqual(result["state"], "modified_source")
        self.assertIn("hermes_cli/plugins.py", result["reasons"][0]["paths"])

    def test_conflicting_installed_dependency_is_refused(self):
        self.install_package("tree-sitter", "0.25.0")
        result = self.inspect()
        self.assertEqual(result["state"], "dependency_conflict")
        self.assertEqual(result["dependencies"]["conflicts"],
                         [{"name": "tree-sitter", "installed": "0.25.0", "required": "0.26.0"}])

    def test_matching_installed_dependency_needs_no_addition(self):
        self.install_package("tree_sitter", "0.26.0")
        result = self.inspect()
        self.assertEqual(result["state"], "compatible")
        self.assertEqual(result["dependencies"], {"add": [], "conflicts": []})

    def test_additional_profiles_are_refused_as_shared_installation(self):
        (self.home / "profiles/work").mkdir(parents=True)
        result = self.inspect()
        self.assertEqual(result["state"], "shared_installation")
        self.assertEqual(result["reasons"][0]["paths"], ["work"])

    def test_selected_named_profile_is_refused_as_shared_installation(self):
        named = self.home / "profiles/work"
        named.mkdir(parents=True)
        result = inspect_host(self.source, load_manifest(self.manifest), hermes_home=named,
                              search_path=[str(self.packages)])
        self.assertEqual(result["state"], "shared_installation")

    def test_installation_without_git_directory_is_unsupported_layout(self):
        subprocess.run(["rm", "-rf", str(self.source / ".git")], check=True)
        result = self.inspect()
        self.assertEqual(result["state"], "unsupported_layout")
        self.assertEqual(self.codes(result), ["not_git_checkout"])
        self.assertIsNone(result["detected"]["commit"])

    def test_linked_worktree_is_unsupported_layout(self):
        linked = self.root / "linked"
        git("worktree", "add", "-q", "--detach", str(linked), cwd=self.source)
        result = inspect_host(linked, load_manifest(self.manifest), hermes_home=self.home,
                              search_path=[str(self.packages)])
        self.assertEqual(result["state"], "unsupported_layout")
        self.assertIn("not_git_checkout", self.codes(result))

    def stamp(self, value):
        ignore = self.source / ".gitignore"
        if "install-stamp.json" not in ignore.read_text():
            self.ignore_stamp()
        (self.source / "install-stamp.json").write_text(value)

    def ignore_stamp(self):
        (self.source / ".gitignore").write_text("venv/\ninstall-stamp.json\n")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qam", "ignore stamp",
            cwd=self.source)
        self.manifest["hermes"][0]["commit"] = git("rev-parse", "HEAD", cwd=self.source)

    def test_self_updating_git_install_stamp_is_compatible(self):
        self.stamp('{"schemaVersion": 2, "source": "git", "distribution": null, "updateMechanism": "self"}\n')
        self.assertEqual(self.inspect()["state"], "compatible")

    def test_packaged_install_stamp_is_unsupported_layout(self):
        for value in ('{"distribution": "docker", "updateMechanism": "external"}\n',
                      '{"distribution": "nix", "updateMechanism": "self"}\n',
                      '{"distribution": null, "updateMechanism": "electron-updater"}\n',
                      'not json\n'):
            with self.subTest(value=value):
                self.stamp(value)
                result = self.inspect()
                self.assertEqual(result["state"], "unsupported_layout")
                self.assertIn("packaged_install", self.codes(result))

    def test_group_writable_source_is_unsupported_layout(self):
        self.source.chmod(0o775)
        result = self.inspect()
        self.assertEqual(result["state"], "unsupported_layout")
        self.assertIn("shared_write_access", self.codes(result))

    def test_group_writable_patch_target_is_unsupported_layout(self):
        (self.source / "hermes_cli/plugins.py").chmod(0o664)
        result = self.inspect()
        self.assertEqual(result["state"], "unsupported_layout")
        self.assertEqual(result["reasons"][0]["code"], "shared_write_access")
        self.assertEqual(result["reasons"][0]["paths"], ["hermes_cli/plugins.py"])

    def test_read_only_source_is_unsupported_layout(self):
        self.source.chmod(0o555)
        self.addCleanup(self.source.chmod, 0o755)
        if os.access(self.source, os.W_OK):
            self.skipTest("The account can write read-only directories")
        result = self.inspect()
        self.assertEqual(result["state"], "unsupported_layout")
        self.assertIn("read_only_source", self.codes(result))

    def test_directory_that_is_not_hermes_is_unsupported_layout(self):
        (self.source / "run_agent.py").unlink()
        result = self.inspect()
        self.assertEqual(result["state"], "unsupported_layout")
        self.assertIn("not_hermes_source", self.codes(result))

    def test_every_independent_refusal_is_reported(self):
        (self.home / "profiles/work").mkdir(parents=True)
        (self.source / "model_tools.py").write_text("TOOLS = ['edited']\n")
        self.install_package("tree-sitter", "0.25.0")
        result = self.inspect()
        self.assertEqual(result["state"], "shared_installation")
        self.assertEqual(self.codes(result), ["shared_installation", "modified_files", "dependency_conflict"])


class InstalledHostTests(unittest.TestCase):
    """Hosts that carry a LifeOS host record are classified against the record, not the fresh-install entry."""

    setUp = HostCompatibilityTests.setUp
    patch = HostCompatibilityTests.patch

    def record(self, **changes):
        from optional.lifeos_release_manager.host_record import build_record
        value = build_record(self.home, self.source, load_manifest(self.manifest)["hermes"][0],
                             operation="e" * 32, version="0.8.0")
        return {**value, **changes}

    def inspect_installed(self, record):
        return inspect_host(self.source, load_manifest(self.manifest), hermes_home=self.home,
                            search_path=[str(self.packages)], record=record)

    def test_recorded_patched_host_is_installed(self):
        self.patch()
        result = self.inspect_installed(self.record())
        self.assertEqual(result["state"], "installed")
        self.assertTrue(result["installed"])
        self.assertFalse(result["compatible"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["qualified"], "v0.0.1")

    def test_recorded_host_with_a_reverted_target_is_drift(self):
        self.patch(added=False)
        result = self.inspect_installed(self.record())
        self.assertEqual(result["state"], "host_drift")
        self.assertEqual(result["reasons"][0]["paths"], ["hermes_cli/new_hook.py"])

    def test_recorded_host_at_another_commit_is_drift(self):
        self.patch()
        result = self.inspect_installed(self.record(commit="f" * 40))
        self.assertEqual(result["state"], "host_drift")
        self.assertFalse(result["installed"])

    def test_recorded_host_in_another_source_is_drift(self):
        self.patch()
        result = self.inspect_installed(self.record(source=str(self.root / "other")))
        self.assertEqual(result["state"], "host_drift")

    def test_recorded_host_with_an_edit_outside_the_targets_is_modified(self):
        self.patch()
        (self.source / "model_tools.py").write_text("TOOLS = ['edited']\n")
        result = self.inspect_installed(self.record())
        self.assertEqual(result["state"], "modified_source")
        self.assertFalse(result["installed"])

    def test_check_reads_the_profile_record(self):
        from optional.lifeos_release_manager import host_compatibility
        from optional.lifeos_release_manager.host_record import record_path
        self.patch()
        record_path(self.home).write_text(json.dumps(self.record()))
        record_path(self.home).chmod(0o600)
        original = host_compatibility.running_source
        host_compatibility.running_source = lambda: self.source
        self.addCleanup(setattr, host_compatibility, "running_source", original)
        self.assertEqual(host_compatibility.check(self.home, manifest=self.manifest,
                                                  search_path=[str(self.packages)])["state"], "installed")


class ManifestTests(unittest.TestCase):
    def valid(self):
        return {"format": 1, "hermes": [{"label": "v1", "commit": "a" * 40,
            "patches": [{"name": "host.patch", "sha256": "b" * 64}],
            "files": {"hermes_cli/x.py": {"stock": "c" * 64, "patched": "d" * 64}}}],
            "dependencies": [{"name": "tree-sitter", "version": "0.26.0"}]}

    def test_accepts_valid_manifest(self):
        self.assertEqual(load_manifest(self.valid())["hermes"][0]["label"], "v1")

    def test_refuses_malformed_entries(self):
        cases = []
        value = self.valid(); value["format"] = 2; cases.append(value)
        value = self.valid(); value["hermes"][0]["commit"] = "a" * 39; cases.append(value)
        value = self.valid(); value["hermes"][0]["files"] = {"../escape.py": {"stock": None, "patched": "d" * 64}}
        cases.append(value)
        value = self.valid(); value["hermes"][0]["files"] = {"/abs.py": {"stock": None, "patched": "d" * 64}}
        cases.append(value)
        value = self.valid(); value["hermes"][0]["files"]["hermes_cli/x.py"]["patched"] = None; cases.append(value)
        value = self.valid(); value["hermes"][0]["files"]["hermes_cli/x.py"]["stock"] = "d" * 64; cases.append(value)
        value = self.valid(); value["hermes"][0]["files"] = {}; cases.append(value)
        value = self.valid(); value["dependencies"] = [{"name": "x", "version": ">=1"}]; cases.append(value)
        value = self.valid(); value["extra"] = True; cases.append(value)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ManifestRejected):
                load_manifest(value)


if __name__ == "__main__":
    unittest.main()
