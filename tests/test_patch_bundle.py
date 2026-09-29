# ABOUTME: Checks that installable plugin files include the supported LifeOS patches.
# ABOUTME: Rejects a plugin build whose bundled patches differ from source preparation.

import unittest
from pathlib import Path

from lifeos_hook_bridge.install_source import (
    HERMES_PATCHES, LIFEOS_PATCHES, SUPPORTED_HERMES_COMMIT, SUPPORTED_LIFEOS_COMMIT,
)
from scripts.prepare_sources import SOURCES


ROOT = Path(__file__).resolve().parents[1]


class PatchBundleTests(unittest.TestCase):
    def test_runtime_contains_exact_hermes_patch_sequence(self):
        self.assertEqual(SUPPORTED_HERMES_COMMIT, SOURCES["hermes"]["base"])
        self.assertEqual(HERMES_PATCHES, SOURCES["hermes"]["patches"])
        for name in HERMES_PATCHES:
            with self.subTest(name=name):
                runtime = ROOT / "lifeos_hook_bridge/patches" / name
                self.assertEqual(runtime.read_bytes(), (ROOT / "patches" / name).read_bytes())

    def test_runtime_contains_exact_lifeos_patch_sequence(self):
        self.assertEqual(SUPPORTED_LIFEOS_COMMIT, SOURCES["lifeos"]["base"])
        self.assertEqual(LIFEOS_PATCHES, SOURCES["lifeos"]["patches"])
        for name in SOURCES["lifeos"]["patches"]:
            with self.subTest(name=name):
                runtime = ROOT / "lifeos_hook_bridge/patches" / name
                self.assertEqual(runtime.read_bytes(), (ROOT / "patches" / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
