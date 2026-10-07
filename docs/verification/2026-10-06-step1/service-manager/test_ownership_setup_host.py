# ABOUTME: Runs fresh Hermes processes after coordinated service draining and ownership publication.
# ABOUTME: Verifies preserved built-in stores and actual model request delivery through a local endpoint.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.ownership_setup import OwnershipSetup
from test_memory_ownership import install_connector
import test_memory_host as host_fixture
import test_profile_services as service_fixture


class OwnershipSetupHostTests(unittest.TestCase):
    def test_restarted_profile_uses_native_tools_and_returns_to_preserved_hermes_memory(self):
        fixture = host_fixture.MemoryHostTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        configuration = MemoryConfiguration(fixture.fixture.fixture.path)
        configuration.update(lambda value: value.update(ownership_enabled=False,
            accounts={**value['accounts'], 'dashboard:owner': 'owner'}))
        install_connector(configuration)
        profile = fixture.home
        config = {**fixture.fixture.host_config, 'memory': {'provider': None},
            'plugins': {'enabled': ['lifeos-hook-bridge']}}
        config['model'] = {**config['model'], 'streaming': False, 'context_length': 131072}
        (profile / 'config.yaml').write_text(json.dumps(config))
        original = (profile / 'config.yaml').read_bytes()
        services = service_fixture.ProfileServicesTests()
        services.fixture_home = fixture.fixture.fixture.fixture.home
        services.fixture_profile = profile
        services.setUp()
        self.addCleanup(services.doCleanups)

        def probe(operation=''):
            environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
            environment.update(HOME=str(fixture.fixture.fixture.fixture.home), HERMES_HOME=str(profile),
                LIFEOS_HERMES_SOURCE=str(host_fixture.model_fixture.HOST),
                LIFEOS_HOOK_SETTINGS=str(fixture.fixture.fixture.fixture.root / 'settings.json'),
                BUN_CONFIG_NO_AUTO_INSTALL='1')
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_host_calls.py'))],
                input=json.dumps({'route': fixture.fixture.route, 'operation': operation,
                    'message': 'Synthetic coordinated ownership verification message'}),
                text=True, capture_output=True, env=environment, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            value = json.loads(result.stdout)
            self.assertEqual(value['warnings'], '')
            return value

        operation = OwnershipSetup(configuration, units=services.units)
        before = probe()
        self.assertTrue(before['has_builtin_store'])
        plan = operation.prepare(fixture.fixture.fixture.fixture.home / 'coordinated-backup', account='dashboard:owner')
        applied = operation.apply(plan['signature'], account='dashboard:owner')
        selected = probe()
        self.assertFalse(selected['has_builtin_store'])
        self.assertEqual(selected['providers'], ['lifeos-hook-bridge'])
        self.assertNotIn('memory', selected['tools'])
        self.assertIn('lifeos_memory_remember', selected['tools'])
        self.assertIn('skill_manage', selected['tools'])
        self.assertTrue(all(value['success'] is False for value in selected['disabled_writes']))
        conversation = probe('conversation')
        self.assertEqual(conversation['conversation']['final_response'], 'SYNTHETIC-MODEL-OK')
        calls = [item for item in fixture.fixture.received if item['path'] == '/v1/chat/completions']
        self.assertEqual(len(calls), 1)
        returned = operation.recover(account='dashboard:owner')
        restored = probe()
        self.assertTrue(restored['has_builtin_store'])
        self.assertEqual(restored['providers'], [])
        self.assertEqual((profile / 'config.yaml').read_bytes(), original)
        for name, content in fixture.original.items():
            self.assertEqual((profile / 'memories' / name).read_bytes(), content)
            self.assertIn(content.decode().strip(), before['prompt'])
            self.assertNotIn(content.decode().strip(), selected['prompt'])
            self.assertNotIn(content.decode().strip(), json.dumps(calls[0]['body']))
            self.assertIn(content.decode().strip(), restored['prompt'])
        self.assertTrue(all(services.properties(role)['MainPID'] != '0' for role in services.units))
        directory = os.environ.get('LIFEOS_SETUP_EVIDENCE_DIR')
        if directory:
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            (target / (self._testMethodName + '.json')).write_text(json.dumps({'before': before,
                'reviewed': plan, 'applied': applied, 'selected': selected, 'conversation': conversation,
                'returned': returned, 'restored': restored, 'model_calls': calls,
                'journal': json.loads(operation.journal.read_text())}, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
