# ABOUTME: Checks that Hermes SessionStart triggers LifeOS's freshness cache writer.
# ABOUTME: Uses a disposable LifeOS directory and verifies the resulting schema.

import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge


FRESHNESS_PATH = os.environ.get("LIFEOS_FRESHNESS_CACHE_PATH")


@unittest.skipUnless(FRESHNESS_PATH and shutil.which("bun"), "LifeOS FreshnessCache and Bun are required")
class NativeFreshnessCacheTests(unittest.TestCase):
    def test_session_start_writes_freshness_cache(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-freshness-") as directory:
            root = Path(directory)
            telos = root / "LIFEOS/USER/TELOS/TELOS.md"
            telos.parent.mkdir(parents=True)
            today = date.today().isoformat()
            telos.write_text(
                f"---\nlast_updated: {today}\nlast_reviewed: {today}\n"
                "last_reviewed_by: test\n---\n# Test TELOS\n"
            )
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {
                "SessionStart": [{"hooks": [{
                    "type": "command", "command": f"bun {FRESHNESS_PATH} --quiet",
                }]}],
            }}))
            bridge = HookBridge(settings, root)
            try:
                bridge.pre_llm_call("Begin", session_id="freshness-probe")
            finally:
                bridge.close()

            cache = root / "LIFEOS/USER/CACHE/freshness.json"
            payload = json.loads(cache.read_text())
            self.assertEqual(payload["total"], len(payload["files"]))
            telos_row = next(row for row in payload["files"] if row["slug"] == "telos")
            self.assertFalse(telos_row["stale"])
            self.assertGreater(payload["fresh_count"], 0)
            self.assertIn("generated_at", payload)
