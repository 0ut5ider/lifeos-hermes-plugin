# ABOUTME: Checks that every pinned LifeOS hook registration has a tracked parity row.
# ABOUTME: Detects new or changed registrations before an updated LifeOS install is accepted.

import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_hook_inventory import check_inventory


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/parity/public-hooks.json"
ROWS = ROOT / "docs/parity/registrations.csv"


class HookInventoryTests(unittest.TestCase):
    def test_pinned_lifeos_manifest_has_a_row_for_every_registration(self):
        self.assertEqual(check_inventory(MANIFEST, ROWS), [])

    def test_added_registration_fails_the_inventory_gate(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["hooks"]["PreToolUse"].append({
            "matcher": "Read", "hooks": [{"type": "command", "command": "synthetic-review-hook"}],
        })
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "settings.json"
            changed.write_text(json.dumps(manifest))
            errors = check_inventory(changed, ROWS)
        self.assertTrue(any("synthetic-review-hook" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
