# ABOUTME: Verifies the complete host extension can be regenerated from a prepared source tree.
# ABOUTME: Uses the real owned source checkout and rejects incomplete patch inventories.
import os
from pathlib import Path
import tempfile
import unittest
from scripts.rebuild_hermes_patches import rebuild
from lifeos_hook_bridge.install_source import HERMES_PATCHES

SOURCE = Path(os.environ.get('LIFEOS_HERMES_REBUILD_SOURCE', str(Path.home() / '.cache/lifeos-plugin-memory/source-gate-20260930-proposals-fixed/hermes')))

@unittest.skipUnless((SOURCE / '.git').exists(), 'A prepared source checkout with new files marked for diff is required')
class HermesPatchRegenerationTests(unittest.TestCase):
    def test_regeneration_publishes_the_complete_ordered_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            rebuild(SOURCE, output)
            self.assertEqual({path.name for path in output.iterdir()}, set(HERMES_PATCHES))
            patch = (output / 'hermes-required-middleware.patch').read_text()
            self.assertIn('admit_llm_request', patch)
            self.assertIn('test_required_middleware.py', patch)
            self.assertIn('REQUIRED_MIDDLEWARE_API_VERSION', patch)
            self.assertIn('agent/turn_request_assembly.py', patch)
