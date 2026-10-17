# ABOUTME: Checks generation of the Hermes compatibility manifest and the shipped manifest's bindings.
# ABOUTME: Builds entries from real Git archives and compares the shipped file with the canonical patches.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from lifeos_hook_bridge import PATCHED_HOOKS
from lifeos_hook_bridge.install_source import HERMES_PATCHES, SUPPORTED_HERMES_COMMIT
from optional.lifeos_release_manager.host_compatibility import MANIFEST, load_manifest
from scripts.build_host_compatibility import (ManifestBuildError, bridge_capabilities, build_entry, build_manifest,
                                              plugin_dependencies)


REPOSITORY = Path(__file__).resolve().parents[1]


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ManifestBuildTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        source = self.root / "hermes"
        (source / "hermes_cli").mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=source)
        (source / "hermes_cli/plugins.py").write_text("VALID_HOOKS = {'pre_tool_call'}\n")
        (source / "model_tools.py").write_text("TOOLS = []\n")
        (source / "pm").mkdir()
        (source / "pm/lock.json").write_text(json.dumps({"packages": {"python": {"version": "3.14.7+20260901"}}}))
        git("add", ".", cwd=source)
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base", cwd=source)
        self.commit = git("rev-parse", "HEAD", cwd=source)
        self.source = source
        self.archive = self.root / "stock-hermes.tgz"
        with self.archive.open("wb") as output:
            subprocess.run(["git", "archive", "--format=tar.gz", self.commit], cwd=source, stdout=output, check=True)
        self.patches = self.root / "patches"
        self.patches.mkdir()
        (source / "hermes_cli/plugins.py").write_text("VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n")
        (source / "hermes_cli/new_hook.py").write_text("ENABLED = True\n")
        git("add", "-N", "hermes_cli/new_hook.py", cwd=source)
        (self.patches / "host.patch").write_text(git("diff", cwd=source) + "\n")
        git("reset", "-q", cwd=source)
        (source / "hermes_cli/new_hook.py").unlink()
        git("checkout", "--", ".", cwd=source)
        (source / "model_tools.py").write_text("TOOLS = ['second']\n")
        (self.patches / "second.patch").write_text(git("diff", cwd=source) + "\n")
        git("checkout", "--", ".", cwd=source)
        self.capabilities = {"hooks": ["pre_turn_stop"], "middleware_api": 1}

    def build(self, names=("host.patch",), **options):
        return build_entry(self.archive, self.patches, names, "v0.0.1", self.commit,
                           capabilities=self.capabilities, **options)

    def test_entry_records_stock_and_patched_hashes_of_every_changed_file(self):
        entry = self.build(("host.patch", "second.patch"))
        self.assertEqual(entry["commit"], self.commit)
        self.assertEqual(entry["label"], "v0.0.1")
        self.assertEqual([patch["name"] for patch in entry["patches"]], ["host.patch", "second.patch"])
        self.assertEqual(entry["patches"][0]["sha256"], digest((self.patches / "host.patch").read_bytes()))
        self.assertEqual(entry["files"], {
            "hermes_cli/new_hook.py": {"stock": None, "patched": digest(b"ENABLED = True\n")},
            "hermes_cli/plugins.py": {"stock": digest(b"VALID_HOOKS = {'pre_tool_call'}\n"),
                                      "patched": digest(b"VALID_HOOKS = {'pre_tool_call', 'pre_turn_stop'}\n")},
            "model_tools.py": {"stock": digest(b"TOOLS = []\n"), "patched": digest(b"TOOLS = ['second']\n")},
        })

    def test_entry_declares_the_pinned_interpreter_and_the_capabilities(self):
        entry = self.build()
        self.assertEqual(entry["python"], "3.14")
        self.assertEqual(entry["capabilities"], self.capabilities)
        self.assertNotIn("known_conflicts", entry)

    def test_entry_records_known_conflicts_when_given(self):
        entry = self.build(known_conflicts=["The example-relay plugin replaces the delivery hook."])
        self.assertEqual(entry["known_conflicts"], ["The example-relay plugin replaces the delivery hook."])

    def test_archive_without_an_interpreter_pin_is_refused(self):
        (self.source / "pm/lock.json").unlink()
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qam", "drop", cwd=self.source)
        self.commit = git("rev-parse", "HEAD", cwd=self.source)
        with self.archive.open("wb") as output:
            subprocess.run(["git", "archive", "--format=tar.gz", self.commit], cwd=self.source, stdout=output, check=True)
        with self.assertRaisesRegex(ManifestBuildError, "Python"):
            self.build()

    def test_bridge_capabilities_name_the_patched_hooks(self):
        self.assertEqual(bridge_capabilities(), {"hooks": sorted(PATCHED_HOOKS), "middleware_api": 1})

    def test_archive_from_another_commit_is_refused(self):
        with self.assertRaisesRegex(ManifestBuildError, "commit"):
            build_entry(self.archive, self.patches, ("host.patch",), "v0.0.1", "f" * 40, capabilities=self.capabilities)

    def test_patch_that_does_not_apply_is_refused(self):
        (self.patches / "broken.patch").write_text((self.patches / "host.patch").read_text().replace(
            "pre_tool_call'}", "missing'}", 1))
        with self.assertRaisesRegex(ManifestBuildError, "broken.patch"):
            self.build(("broken.patch",))

    def test_plugin_dependencies_require_exact_pins(self):
        plugin = self.root / "plugin.yaml"
        plugin.write_text("name: bridge\npython_dependencies:\n  - tree-sitter==0.26.0\n  - mcp==2.0.0\n")
        self.assertEqual(plugin_dependencies(plugin), [{"name": "tree-sitter", "version": "0.26.0"},
                                                       {"name": "mcp", "version": "2.0.0"}])
        plugin.write_text("name: bridge\npython_dependencies:\n  - tree-sitter>=0.26\n")
        with self.assertRaisesRegex(ManifestBuildError, "exact"):
            plugin_dependencies(plugin)

    def test_built_manifest_passes_validation(self):
        plugin = self.root / "plugin.yaml"
        plugin.write_text("name: bridge\npython_dependencies:\n  - tree-sitter==0.26.0\n")
        entry = self.build()
        manifest = build_manifest([entry], plugin)
        self.assertEqual(load_manifest(manifest), manifest)


class ShippedManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(MANIFEST)
        self.entry = self.manifest["hermes"][0]

    def test_binds_the_supported_commit_and_canonical_patch_order(self):
        self.assertEqual(len(self.manifest["hermes"]), 1)
        self.assertEqual(self.entry["commit"], SUPPORTED_HERMES_COMMIT)
        patches = REPOSITORY / "lifeos_hook_bridge/patches"
        self.assertEqual(self.entry["patches"], [{"name": name, "sha256": digest((patches / name).read_bytes())}
                                                 for name in HERMES_PATCHES])

    def test_declares_the_bridge_capabilities(self):
        self.assertEqual(self.entry["capabilities"], bridge_capabilities())

    def test_binds_the_bridge_dependencies(self):
        self.assertEqual(self.manifest["dependencies"],
                         plugin_dependencies(REPOSITORY / "lifeos_hook_bridge/plugin.yaml"))

    def test_matches_a_rebuild_from_the_stock_archive(self):
        archive = os.environ.get("LIFEOS_STOCK_HERMES_ARCHIVE")
        if not archive:
            self.skipTest("Set LIFEOS_STOCK_HERMES_ARCHIVE to the qualified stock-hermes.tgz to rebuild the entry")
        entry = build_entry(Path(archive), REPOSITORY / "lifeos_hook_bridge/patches", HERMES_PATCHES,
                            self.entry["label"], SUPPORTED_HERMES_COMMIT, capabilities=bridge_capabilities(),
                            known_conflicts=self.entry.get("known_conflicts"))
        self.assertEqual(entry, self.entry)
        self.assertEqual(MANIFEST.read_text(), json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
