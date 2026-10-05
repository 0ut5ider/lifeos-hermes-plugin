# ABOUTME: Checks real Hermes configuration failures against lasting-store ownership.
# ABOUTME: Retains ordinary defaults and selected flags while refusing malformed and unreadable configurations.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class HermesMemoryConfigTests(unittest.TestCase):
    def call(self, configuration, operation='read', target='memory'):
        with tempfile.TemporaryDirectory(prefix='hermes-memory-config-') as directory:
            home = Path(directory)
            (home / 'memories').mkdir()
            (home / 'memories/MEMORY.md').write_text('Synthetic retained memory.\n')
            (home / 'memories/USER.md').write_text('Synthetic retained profile.\n')
            if configuration == 'directory':
                (home / 'config.yaml').mkdir()
            elif configuration is not None:
                (home / 'config.yaml').write_text(configuration)
            host = Path(os.environ['LIFEOS_HERMES_SOURCE'])
            environment = {**os.environ, 'HERMES_HOME': str(home), 'HOME': str(home),
                'PYTHONPATH': str(host), 'PYTHONDONTWRITEBYTECODE': '1'}
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('hermes_memory_config_process.py'))],
                input=json.dumps({'operation': operation, 'target': target}), env=environment,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            return json.loads(result.stdout)

    def test_invalid_configurations_do_not_enable_or_write_lasting_stores(self):
        invalid = [('memory: []\n', False), ('memory: synthetic-invalid\n', False), ('memory: null\n', False),
            ('memory: [\n', True), ('directory', True)]
        for configuration, warning in invalid:
            for target in ('memory', 'user'):
                with self.subTest(configuration=configuration, target=target):
                    result = self.call(configuration, 'write', target)
                    self.assertEqual(result['flags'], [False, False], result)
                    self.assertEqual(result['store_flags'], [False, False], result)
                    self.assertFalse(result['result']['success'], result)
                    self.assertTrue(result['unchanged'], result)
                    if warning:
                        self.assertIn('config.yaml', result['warnings'])
                    else:
                        self.assertEqual(result['warnings'], '')
        for value in ('[false]', '{unexpected: true}', 'null', '.nan', '.inf'):
            with self.subTest(flag=value):
                result = self.call('memory:\n  memory_enabled: ' + value + '\n  user_profile_enabled: false\n', 'write')
                self.assertEqual(result['flags'], [False, False], result)
                self.assertEqual(result['store_flags'], [False, False], result)
                self.assertFalse(result['result']['success'], result)
                self.assertTrue(result['unchanged'], result)
        bad_limit = 'memory:\n  memory_enabled: false\n  user_profile_enabled: false\n  memory_char_limit: invalid\n'
        result = self.call(bad_limit, 'write')
        self.assertEqual(result['flags'], [False, False], result)
        self.assertEqual(result['store_flags'], [False, False], result)
        self.assertFalse(result['result']['success'], result)
        self.assertTrue(result['unchanged'], result)

    def test_valid_selected_flags_and_fresh_defaults_retain_native_behavior(self):
        for configuration, expected in [(None, [True, True]), ('{}\n', [True, True]),
                ('memory:\n  memory_enabled: false\n  user_profile_enabled: true\n', [False, True]),
                ('memory:\n  memory_enabled: true\n  user_profile_enabled: false\n', [True, False])]:
            with self.subTest(configuration=configuration):
                result = self.call(configuration)
                self.assertEqual(result['flags'], expected, result)
                self.assertEqual(result['store_flags'], expected, result)
                self.assertTrue(result['unchanged'], result)
                self.assertEqual(result['warnings'], '')
