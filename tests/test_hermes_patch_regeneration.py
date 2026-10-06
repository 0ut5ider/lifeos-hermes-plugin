# ABOUTME: Verifies the complete host extension can be regenerated from a prepared source tree.
# ABOUTME: Uses the real owned source checkout and rejects incomplete patch inventories.
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from scripts.rebuild_hermes_patches import rebuild
from lifeos_hook_bridge.install_source import HERMES_PATCHES

SOURCE = Path(os.environ.get('LIFEOS_HERMES_REBUILD_SOURCE', str(Path.home() / '.cache/lifeos-full-experience-20261005/validator-fix/hermes')))

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
            self.assertIn('hermes_cli/plugin_validate.py', patch)
            self.assertIn('test_capability_probe_records_required_middleware', patch)
            web = (output / 'hermes-web-result-status.patch').read_text()
            self.assertIn('def web_extract_result_failed', web)
            self.assertIn('a/agent/display.py', web)
            self.assertIn('a/agent/tool_guardrails.py', web)
            self.assertIn('a/agent/tool_result_classification.py', web)

    def test_regenerated_bundle_recreates_the_prepared_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'patches'
            rebuild(SOURCE, output)
            candidate = root / 'candidate'
            subprocess.run(['git', 'clone', '--quiet', '--no-checkout', str(SOURCE), str(candidate)], check=True)
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
            subprocess.run(['git', 'checkout', '--quiet', '--detach', revision], cwd=candidate, check=True)
            for name in HERMES_PATCHES:
                subprocess.run(['git', 'apply', '--check', str(output / name)], cwd=candidate, check=True)
                subprocess.run(['git', 'apply', str(output / name)], cwd=candidate, check=True)
            subprocess.run(['git', 'diff', '--check'], cwd=candidate, check=True)
            changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=SOURCE, text=True).splitlines()
            for name in changed:
                with self.subTest(path=name):
                    self.assertEqual((candidate / name).read_bytes(), (SOURCE / name).read_bytes())
