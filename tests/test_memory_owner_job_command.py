# ABOUTME: Runs owner jobs through actual Hermes plugin discovery and its command parser.
# ABOUTME: Checks selected-profile policy and preserves Hermes files during native synthesis.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_host as host_fixture
import test_memory_model_calls as model_fixture
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_transaction import publish


class MemoryOwnerJobCommandTests(unittest.TestCase):
    def setUp(self):
        self.fixture = host_fixture.MemoryHostTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native = self.fixture.fixture.fixture.fixture
        self.configuration = MemoryConfiguration(self.fixture.fixture.fixture.path)
        grant = {'visibility': 'private', 'participants': ['owner'],
            'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
            'projects': ['*'], 'model_routes': [route_identity(**self.fixture.fixture.route)]}
        self.configuration.update(lambda value: value.update(
            accounts={**value['accounts'], f'terminal:{os.getuid()}': 'owner'},
            destinations={**value['destinations'], 'terminal:' + str(self.fixture.home): grant}))
        settings = {**self.fixture.fixture.host_config, 'plugins': {'enabled': ['lifeos-hook-bridge']},
            'memory': {'memory_enabled': False, 'user_profile_enabled': False}}
        (self.fixture.home / 'config.yaml').write_text(json.dumps(settings))
        connector = self.native.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        publish(connector, json.dumps({'version': 1, 'command': [sys.executable,
            str(self.fixture.home / 'plugins/lifeos-hook-bridge/memory_rpc.py'),
            '--configuration', str(self.configuration.path)]}).encode())
        self.ratings = self.native.root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        self.ratings.parent.mkdir(parents=True)
        publish(self.ratings, (json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'rating': 8,
            'session_id': 'synthetic-cli-rating', 'source': 'explicit',
            'sentiment_summary': 'Synthetic clear implementation', 'confidence': 0.9}) + '\n').encode())
        self.synthesis = self.native.root / 'LIFEOS/MEMORY/LEARNING/SYNTHESIS'

    def call(self, name='memory-consolidation'):
        environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
        environment.update(HOME=str(self.native.home), HERMES_HOME=str(self.fixture.home),
            PYTHONPATH=str(model_fixture.HOST), LIFEOS_HOOK_SETTINGS=str(self.native.root / 'settings.json'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        return subprocess.run([sys.executable, '-m', 'hermes_cli.main', 'lifeos-job', name],
            env=environment, capture_output=True, text=True, timeout=40)

    def test_actual_parser_publishes_weekly_synthesis_under_selected_owner_grant(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['status'], 'completed')
        reports = list(self.synthesis.rglob('*.md'))
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].stat().st_mode & 0o777, 0o600)
        for name, content in self.fixture.original.items():
            self.assertEqual((self.fixture.home / 'memories' / name).read_bytes(), content)
        self.assertEqual(self.fixture.fixture.received, [])

    def test_actual_parser_refuses_disabled_ownership_without_native_writes(self):
        self.configuration.update(lambda value: value.update(ownership_enabled=False))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['status'], 'rejected')
        self.assertEqual(result.stderr, '')
        self.assertFalse(self.synthesis.exists())

    def test_actual_parser_refuses_arbitrary_job_before_native_writes(self):
        result = self.call('unexpected-program')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.synthesis.exists())


if __name__ == '__main__':
    unittest.main()
