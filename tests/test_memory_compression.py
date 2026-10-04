# ABOUTME: Verifies complete compression rotation and LifeOS admission on the real Hermes session database.
# ABOUTME: Captures actual summary and continuation requests with a scripted local model endpoint.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_host as host_fixture
import test_memory_model_calls as model_fixture


class MemoryCompressionTests(unittest.TestCase):
    def test_actual_compression_rotates_and_continues_the_verified_conversation(self):
        self.compression(in_place=False)

    def test_actual_in_place_compression_keeps_the_verified_conversation(self):
        self.compression(in_place=True)

    def compression(self, *, in_place):
        fixture = host_fixture.MemoryHostTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        config = {**fixture.fixture.host_config, 'plugins': {'enabled': ['lifeos-hook-bridge']},
                  'memory': {'provider': 'lifeos-hook-bridge', 'memory_enabled': False, 'user_profile_enabled': False},
                  'compression': {'enabled': True, 'in_place': in_place, 'protect_first_n': 1, 'protect_last_n': 2,
                                  'min_tail_user_messages': 1, 'abort_on_summary_failure': True},
                  'model': {**fixture.fixture.host_config['model'], 'streaming': False, 'context_length': 131072}}
        (fixture.home / 'config.yaml').write_text(json.dumps(config))
        environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
        environment.update(HOME=str(fixture.fixture.fixture.fixture.home), HERMES_HOME=str(fixture.home),
                           LIFEOS_HERMES_SOURCE=str(model_fixture.HOST),
                           LIFEOS_HOOK_SETTINGS=str(fixture.fixture.fixture.fixture.root / 'settings.json'),
                           BUN_CONFIG_NO_AUTO_INSTALL='1')
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_compression_calls.py'))],
                                input=json.dumps({'route': fixture.fixture.route}), env=environment,
                                capture_output=True, text=True, timeout=60)
        if os.environ.get('LIFEOS_COMPRESSION_EVIDENCE_DIR'):
            directory = Path(os.environ['LIFEOS_COMPRESSION_EVIDENCE_DIR']) / ('in-place' if in_place else 'rotation')
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'outcome.json').write_text(result.stdout)
            (directory / 'requests.json').write_text(json.dumps(fixture.fixture.received, indent=2) + '\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        outcome = json.loads(result.stdout)
        if outcome['database_warnings']:
            self.assertEqual(len(outcome['database_warnings'].splitlines()), 1)
            self.assertIn('WAL-reset corruption bug', outcome['database_warnings'])
            self.assertIn('using journal_mode=DELETE', outcome['database_warnings'])
            self.assertEqual(outcome['journal_mode'], 'delete')
        information = {key: outcome[key] for key in ('parent', 'child', 'diagnostics')}
        if in_place:
            self.assertEqual(outcome['parent'], outcome['child'], information)
        else:
            self.assertNotEqual(outcome['parent'], outcome['child'], information)
            self.assertEqual(outcome['child_row']['parent_session_id'], outcome['parent'])
        information['response'] = outcome['continuation'].get('final_response')
        self.assertFalse(outcome['continuation'].get('failed'), information)
        self.assertNotEqual(outcome['continuation'].get('turn_exit_reason'), 'prompt_blocked', information)
        self.assertEqual(outcome['continuation']['final_response'], 'SYNTHETIC-MODEL-OK')
        self.assertNotIn('failed', outcome['diagnostics'])
        self.assertEqual(outcome['admission_trace'], [])
        self.assertIn('Compacting context', outcome['diagnostics'])
        calls = [request for request in fixture.fixture.received if request['path'] == '/v1/chat/completions']
        foreground = [request for request in calls if 'LifeOS owns lasting memory' in
                      str(request['body'].get('messages', [{}])[0].get('content'))]
        self.assertEqual(len(foreground), 7)
        self.assertGreaterEqual(len(calls), 8)
