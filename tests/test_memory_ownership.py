# ABOUTME: Verifies reviewed ownership configuration changes on private synthetic profiles.
# ABOUTME: Checks exact configuration recovery while native facts and forget decisions remain current.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from ruamel.yaml import YAML

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.profile_backup import create
import test_profile_backup as fixture_module
import test_memory_native as native_fixture


def install_connector(configuration):
    path = Path(configuration.load()['root']) / 'LIFEOS/USER/CONFIG/memory-access.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'version': 1, 'command': [sys.executable,
        str(Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_rpc.py'),
        '--configuration', str(configuration.path)]}))
    path.chmod(0o600)
    return path


class MemoryOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.ProfileBackupTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.configuration
        self.configuration.update(lambda value: value.update(ownership_enabled=False,
            accounts={**value['accounts'], 'dashboard:owner': 'owner'}))
        self.profile = self.fixture.profile
        self.original = {name: (self.profile / name).read_bytes()
            for name in ('config.yaml', 'lifeos-memory.json')}
        self.connector = install_connector(self.configuration)
        self.backup = create(self.configuration, self.fixture.destination, account='dashboard:owner')

    def tearDown(self):
        directory = os.environ.get('LIFEOS_OWNERSHIP_EVIDENCE_DIR')
        if directory:
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            files = {name: {'sha256': hashlib.sha256((self.profile / name).read_bytes()).hexdigest(),
                'mode': (self.profile / name).stat().st_mode & 0o777} for name in self.original}
            record = {'test': self.id(), 'configuration': self.configuration.load(), 'files': files,
                'journal': json.loads(self.transaction().journal.read_text()) if self.transaction().journal.exists() else None}
            (target / (self._testMethodName + '.json')).write_text(json.dumps(record, indent=2) + '\n')

    def transaction(self):
        from lifeos_hook_bridge.memory_ownership import OwnershipTransaction
        return OwnershipTransaction(self.configuration)

    def preview(self):
        return self.transaction().preview(Path(self.backup['snapshot']), self.backup['signature'],
            account='dashboard:owner')

    def apply(self, plan=None):
        plan = plan or self.preview()
        return self.transaction().apply(Path(self.backup['snapshot']), self.backup['signature'],
            plan['signature'], account='dashboard:owner')

    def test_reviewed_configuration_disables_both_stores_and_preserves_files(self):
        preview = self.preview()
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), self.original['config.yaml'])
        result = self.apply(preview)
        self.assertEqual(result['state'], 'committed')
        self.assertTrue(result['restart_required'])
        self.assertFalse(result['service_verified'])
        self.assertTrue(self.configuration.load()['ownership_enabled'])
        memory = YAML(typ='safe').load((self.profile / 'config.yaml').read_text())['memory']
        self.assertEqual(memory['provider'], 'lifeos-hook-bridge')
        self.assertIs(memory['memory_enabled'], False)
        self.assertIs(memory['user_profile_enabled'], False)
        for name, content in self.fixture.sources.items():
            if name != 'config.yaml':
                self.assertEqual((self.profile / name).read_bytes(), content)

    def test_recovery_restores_exact_configuration_and_preserves_later_native_writes(self):
        self.apply()
        saved = self.fixture.fixture.fixture.remember('Synthetic later ownership fact', 'ownership-later')
        memory = self.fixture.fixture.fixture.memory
        memory.forget(native_fixture.OWNER, self.fixture.saved['reference'], 'ownership-forget')
        result = self.transaction().rollback(account='dashboard:owner')
        self.assertEqual(result['state'], 'rolled_back')
        for name, content in self.original.items():
            self.assertEqual((self.profile / name).read_bytes(), content)
        self.assertEqual(memory.get(native_fixture.OWNER, saved['reference'])['content'],
            'Synthetic later ownership fact')
        self.assertEqual(memory.recall(native_fixture.OWNER, 'coherent profile backup'), [])

    def test_review_refuses_changed_configuration_or_backup_without_publication(self):
        plan = self.preview()
        path = self.profile / 'config.yaml'
        path.write_text(path.read_text() + 'synthetic_other_setting: preserved\n')
        before = self.configuration.path.read_bytes()
        with self.assertRaises(MemoryUnavailable):
            self.apply(plan)
        self.assertEqual(self.configuration.path.read_bytes(), before)
        self.assertIn('synthetic_other_setting', path.read_text())
        path.write_bytes(self.original['config.yaml'])
        copy = Path(self.backup['snapshot']) / 'profile/files/0'
        copy.write_bytes(b'Synthetic changed backup copy')
        with self.assertRaises(MemoryUnavailable):
            self.apply(plan)
        self.assertEqual(self.configuration.path.read_bytes(), before)

    def test_recovery_preserves_later_configuration_edits(self):
        self.apply()
        changed = self.profile / 'config.yaml'
        changed.write_text(changed.read_text() + 'synthetic_later: true\n')
        before = self.configuration.path.read_bytes()
        with self.assertRaisesRegex(MemoryUnavailable, 'later'):
            self.transaction().rollback(account='dashboard:owner')
        self.assertEqual(self.configuration.path.read_bytes(), before)
        self.assertIn('synthetic_later', changed.read_text())

    def test_edit_during_recovery_is_preserved_before_the_second_publication(self):
        self.apply()
        changed = self.profile / 'config.yaml'
        made_edit = False
        def trace(frame, event, argument):
            nonlocal made_edit
            if (not made_edit and event == 'return' and frame.f_code.co_name == 'publish'
                    and frame.f_locals.get('path') == self.configuration.path):
                made_edit = True
                changed.write_text(changed.read_text() + 'synthetic_during_recovery: true\n')
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaisesRegex(MemoryUnavailable, 'later'):
                self.transaction().rollback(account='dashboard:owner')
        finally:
            sys.settrace(None)
        self.assertTrue(made_edit)
        self.assertIn('synthetic_during_recovery', changed.read_text())
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_edit_after_disabling_stores_prevents_ownership_from_becoming_enabled(self):
        plan = self.preview()
        changed = self.profile / 'config.yaml'
        made_edit = False
        def trace(frame, event, argument):
            nonlocal made_edit
            if (not made_edit and event == 'return' and frame.f_code.co_name == 'publish'
                    and frame.f_locals.get('path') == changed):
                made_edit = True
                changed.write_text(changed.read_text() + 'synthetic_during_setup: true\n')
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):
                self.apply(plan)
        finally:
            sys.settrace(None)
        self.assertTrue(made_edit)
        self.assertIn('synthetic_during_setup', changed.read_text())
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_invalid_journal_metadata_refuses_without_configuration_changes(self):
        self.apply()
        transaction = self.transaction()
        original = transaction.journal.read_bytes()
        before = {name: (self.profile / name).read_bytes() for name in self.original}
        for field, value in [('state', []), ('state', {}), ('version', True), ('entries', None), ('signature', None)]:
            document = json.loads(original)
            document[field] = value
            transaction.journal.write_text(json.dumps(document))
            with self.subTest(field=field, value=value), self.assertRaises(MemoryUnavailable):
                transaction.rollback(account='dashboard:owner')
            for name, content in before.items():
                self.assertEqual((self.profile / name).read_bytes(), content)
        transaction.journal.write_bytes(original)

    def test_setup_requires_owner_disabled_sharing_and_unambiguous_memory_settings(self):
        for account in (None, 'dashboard:other', 'chat-a:100'):
            with self.subTest(account=account), self.assertRaises(PermissionError):
                self.transaction().preview(Path(self.backup['snapshot']), self.backup['signature'], account=account)
        for updates in ({'ownership_enabled': True}, {'sharing_enabled': True}):
            self.configuration.update(lambda value: value.update(updates))
            with self.subTest(updates=updates), self.assertRaises(MemoryUnavailable):
                self.preview()
            self.configuration.path.write_bytes(self.original['lifeos-memory.json'])
        for index, text in enumerate(('memory: null\n', 'memory: []\n',
                'memory:\n  memory_enabled: true\nmemory: {}\n', '[]\n', '"synthetic scalar"\n', '')):
            (self.profile / 'config.yaml').write_text(text)
            snapshot = create(self.configuration, self.fixture.destination.parent / f'invalid-settings-{index}',
                account='dashboard:owner')
            with self.subTest(text=text), self.assertRaises(MemoryUnavailable):
                self.transaction().preview(Path(snapshot['snapshot']), snapshot['signature'], account='dashboard:owner')

    def test_lost_or_changed_connector_refuses_before_ownership_publication(self):
        plan = self.preview()
        original = self.connector.read_bytes()
        self.connector.unlink()
        with self.assertRaises(MemoryUnavailable):
            self.apply(plan)
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), self.original['config.yaml'])
        self.connector.write_bytes(original + b'\n')
        self.connector.chmod(0o600)
        with self.assertRaises(MemoryUnavailable):
            self.apply(plan)
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_process_exit_after_first_file_recovers_configuration_without_data_restore(self):
        plan = self.preview()
        settings = {'configuration': str(self.configuration.path), 'backup': self.backup['snapshot'],
            'backup_signature': self.backup['signature'], 'signature': plan['signature']}
        program = '''import json, os, sys
from pathlib import Path
import lifeos_hook_bridge.memory_ownership as module
from lifeos_hook_bridge.memory_service import MemoryConfiguration
settings = json.loads(sys.stdin.read())
profile = Path(settings['configuration']).parent
def trace(frame, event, argument):
    if event == 'return' and frame.f_code.co_name == 'publish' and frame.f_locals.get('path') == profile / 'config.yaml':
        os._exit(73)
    return trace
sys.settrace(trace)
module.OwnershipTransaction(MemoryConfiguration(Path(settings['configuration']))).apply(
    Path(settings['backup']), settings['backup_signature'], settings['signature'], account='dashboard:owner')
'''
        result = subprocess.run([sys.executable, '-c', program], input=json.dumps(settings),
            text=True, capture_output=True, env=os.environ.copy(), timeout=30)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertIs(YAML(typ='safe').load((self.profile / 'config.yaml').read_text())['memory']['memory_enabled'], False)
        self.assertTrue(self.transaction().status(account='dashboard:owner')['recovery_required'])
        self.transaction().rollback(account='dashboard:owner')
        for name, content in self.original.items():
            self.assertEqual((self.profile / name).read_bytes(), content)
        self.assertEqual(self.fixture.fixture.fixture.memory.get(native_fixture.OWNER,
            self.fixture.saved['reference'])['status'], 'ok')

    def test_process_exit_during_mode_restoration_can_resume_the_original_mode(self):
        self.apply()
        code = '''import json, os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_ownership import OwnershipTransaction
from lifeos_hook_bridge.memory_service import MemoryConfiguration
configuration = MemoryConfiguration(Path(sys.argv[1]))
def trace(frame, event, argument):
    if event == 'return' and frame.f_code.co_name == 'publish' and frame.f_locals.get('path') == configuration.path.parent / 'config.yaml':
        os._exit(73)
    return trace
sys.settrace(trace)
OwnershipTransaction(configuration).rollback(account='dashboard:owner')
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.configuration.path)],
            capture_output=True, text=True, env=os.environ.copy(), timeout=30)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), self.original['config.yaml'])
        self.assertEqual((self.profile / 'config.yaml').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.transaction().status(account='dashboard:owner')['state'], 'restoring')
        self.transaction().rollback(account='dashboard:owner')
        self.assertEqual((self.profile / 'config.yaml').stat().st_mode & 0o777, 0o644)

    def test_current_backup_review_preserves_other_yaml_settings_and_comments(self):
        config = self.profile / 'config.yaml'
        config.write_text('# Synthetic operator comment\nmodel:\n  default: synthetic-model\n'
            'memory:\n  memory_enabled: true\n  user_profile_enabled: true\n'
            '  synthetic_option: "keep this setting" # Synthetic inline comment\n')
        original = config.read_bytes()
        next_backup = create(self.configuration, self.fixture.destination.parent / 'second', account='dashboard:owner')
        transaction = self.transaction()
        plan = transaction.preview(Path(next_backup['snapshot']), next_backup['signature'], account='dashboard:owner')
        transaction.apply(Path(next_backup['snapshot']), next_backup['signature'], plan['signature'], account='dashboard:owner')
        current = config.read_text()
        self.assertIn('# Synthetic operator comment', current)
        self.assertIn('# Synthetic inline comment', current)
        self.assertIn('"keep this setting"', current)
        self.assertEqual(YAML(typ='safe').load(current)['model'], {'default': 'synthetic-model'})
        transaction.rollback(account='dashboard:owner')
        self.assertEqual(config.read_bytes(), original)

    def test_shared_or_merged_memory_settings_require_review_without_changing_other_sections(self):
        documents = [
            'memory: &stores\n  memory_enabled: true\n  user_profile_enabled: true\nsynthetic_other: *stores\n',
            'defaults: &stores\n  memory_enabled: true\n  user_profile_enabled: true\nmemory:\n  <<: *stores\n',
            'defaults: &settings\n  memory: {memory_enabled: true}\n<<: *settings\n',
        ]
        for index, text in enumerate(documents):
            with self.subTest(index=index):
                config = self.profile / 'config.yaml'
                config.write_text(text)
                snapshot = create(self.configuration, self.fixture.destination.parent / f'alias-{index}',
                    account='dashboard:owner')
                with self.assertRaisesRegex(MemoryUnavailable, 'shared|merged'):
                    self.transaction().preview(Path(snapshot['snapshot']), snapshot['signature'], account='dashboard:owner')
                self.assertEqual(config.read_text(), text)
                self.assertFalse(self.configuration.load()['ownership_enabled'])


class HermesOwnershipTests(unittest.TestCase):
    def test_fresh_host_processes_load_the_selected_owner_and_return_to_preserved_stores(self):
        import test_memory_host as host_fixture
        from lifeos_hook_bridge.memory_ownership import OwnershipTransaction
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
        original_config = (profile / 'config.yaml').read_bytes()
        snapshot = create(configuration, fixture.fixture.fixture.fixture.home / 'ownership-backup',
            account='dashboard:owner')
        transaction = OwnershipTransaction(configuration)
        def probe(operation=''):
            environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
            environment.update(HOME=str(fixture.fixture.fixture.fixture.home), HERMES_HOME=str(profile),
                LIFEOS_HERMES_SOURCE=str(host_fixture.model_fixture.HOST),
                LIFEOS_HOOK_SETTINGS=str(fixture.fixture.fixture.fixture.root / 'settings.json'),
                BUN_CONFIG_NO_AUTO_INSTALL='1')
            process = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_host_calls.py'))],
                input=json.dumps({'route': fixture.fixture.route, 'operation': operation,
                    'message': 'Synthetic ownership verification message'}), env=environment,
                text=True, capture_output=True, timeout=45)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(process.stderr, '')
            result = json.loads(process.stdout)
            self.assertEqual(result['warnings'], '')
            return result
        before = probe()
        self.assertTrue(before['has_builtin_store'])
        plan = transaction.preview(Path(snapshot['snapshot']), snapshot['signature'], account='dashboard:owner')
        transaction.apply(Path(snapshot['snapshot']), snapshot['signature'], plan['signature'], account='dashboard:owner')
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
        for content in fixture.original.values():
            self.assertNotIn(content.decode().strip(), json.dumps(calls[0]['body']))
        transaction.rollback(account='dashboard:owner')
        restored = probe()
        self.assertTrue(restored['has_builtin_store'])
        self.assertEqual(restored['providers'], [])
        self.assertEqual((profile / 'config.yaml').read_bytes(), original_config)
        for name, content in fixture.original.items():
            self.assertEqual((profile / 'memories' / name).read_bytes(), content)
            self.assertIn(content.decode().strip(), before['prompt'])
            self.assertNotIn(content.decode().strip(), selected['prompt'])
            self.assertIn(content.decode().strip(), restored['prompt'])
        directory = os.environ.get('LIFEOS_OWNERSHIP_EVIDENCE_DIR')
        if directory:
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            (target / (self._testMethodName + '.json')).write_text(json.dumps({'before': before,
                'selected': selected, 'conversation': conversation, 'restored': restored,
                'model_calls': calls, 'journal': json.loads(transaction.journal.read_text())}, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
