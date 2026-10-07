# ABOUTME: Verifies batch patch schema selection from actual Hermes profile configuration.
# ABOUTME: Preserves the ordinary schema and model routing when an explicit file capability is absent.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE = os.environ.get('LIFEOS_HERMES_SOURCE')


@unittest.skipUnless(SOURCE, 'Prepared Hermes is required')
class InstalledBatchSchemaTests(unittest.TestCase):
    def schema(self, options=None, model='flashnext-w4a16-fp8ple'):
        with tempfile.TemporaryDirectory(prefix='batch-schema-') as directory:
            home = Path(directory)
            profile = home / '.hermes'
            profile.mkdir()
            config = {'model': {'provider': 'custom', 'default': model}}
            if options is not None:
                config['file_tools'] = options
            (profile / 'config.yaml').write_text(json.dumps(config))
            env = {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile), 'PYTHONPATH': str(SOURCE)}
            code = ('import json\nfrom tools.file_tools import _patch_schema_overrides\n'
                    'print(json.dumps(_patch_schema_overrides()))\n')
            result = subprocess.run([sys.executable, '-c', code], env=env, cwd=home,
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            return json.loads(result.stdout)

    def test_default_private_model_keeps_single_file_schema(self):
        self.assertEqual(self.schema(), {})

    def test_default_openai_family_keeps_its_batch_schema(self):
        result = self.schema(model='gpt-fixture')
        self.assertIn('patch', result['parameters']['properties'])

    def test_explicit_batch_capability_exposes_mode_and_patch(self):
        result = self.schema({'patch_format': 'v4a'})
        self.assertIn('mode', result.get('parameters', {}).get('properties', {}))
        self.assertIn('patch', result['parameters']['properties'])
        self.assertEqual(result['parameters']['required'], ['mode'])

    def test_unrecognized_capability_does_not_enable_batch(self):
        self.assertEqual(self.schema({'patch_format': 'unknown'}), {})
        self.assertEqual(self.schema('invalid'), {})
