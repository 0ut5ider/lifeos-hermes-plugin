# ABOUTME: Checks that actual removal service tests do not change packaged checkout evidence.
# ABOUTME: Preserves the generated diagnostic privately and restores the original fixture after a refusal.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


class FixtureIsolationTests(unittest.TestCase):
    def test_actual_removal_service_control_preserves_checkout_fixture(self):
        root = Path(__file__).resolve().parents[3]
        artifact = Path(__file__).with_name('removal-service-layout.json')
        before = artifact.read_bytes()
        mode = artifact.stat().st_mode & 0o777
        command = [sys.executable, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
            'test_removal_services.RemovalServicesTests.test_actual_removed_pulse_definition_keeps_only_hermes_services_active']
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
        after = artifact.read_bytes()
        try:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('Exception ignored', result.stderr)
            self.assertNotIn('ResourceWarning:', result.stderr)
            self.assertEqual(after, before, 'The actual service control changes evidence inside the checkout')
        finally:
            cache = Path('/home/outsider/.cache/lifeos-memory-portability-20261015')
            report = {'before_sha256': hashlib.sha256(before).hexdigest(),
                'after_sha256': hashlib.sha256(after).hexdigest(), 'unchanged': before == after,
                'actual_service_test_exit': result.returncode}
            (cache / ('fixture-isolation-' + ('unchanged' if before == after else 'changed') + '.json')).write_text(json.dumps(report, indent=2) + '\n')
            if before != after:
                (cache / 'fixture-isolation-generated.json').write_bytes(after)
                artifact.write_bytes(before)
                os.chmod(artifact, mode)
