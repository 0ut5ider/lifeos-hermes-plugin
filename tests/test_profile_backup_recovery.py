# ABOUTME: Reconstructs selected Hermes profile snapshots without replacing live files or starting ownership.
# ABOUTME: Verifies history, native references, rebound links, later-write preservation, and interrupted publication.
from contextlib import closing
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable, NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.profile_backup_recovery import recover
import test_profile_backup as profile_fixture
import test_memory_native as native_fixture


class ProfileRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = profile_fixture.ProfileBackupTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.configuration
        self.backup = self.fixture.destination
        self.destination = self.fixture.fixture.fixture.home / 'profile-recovery/one'

    def snapshot(self):
        return self.fixture.snapshot()[0]['signature']

    def recover(self, signature):
        result = recover(self.configuration, self.backup, signature, self.destination)
        candidate = MemoryConfiguration(Path(result['profile']) / self.configuration.path.name).load()
        self.record('recovery', {'receipt': result, 'configuration': {'root': candidate['root'],
            'ownership_enabled': candidate['ownership_enabled'], 'sharing_enabled': candidate['sharing_enabled']},
            'source_configuration_digest': hashlib.sha256(self.configuration.path.read_bytes()).hexdigest(),
            'manifest': json.loads(Path(result['recovery_manifest']).read_text())})
        return result

    def record(self, name, outcome):
        directory = os.environ.get('LIFEOS_PROFILE_RECOVERY_EVIDENCE_DIR')
        if directory:
            destination = Path(directory) / self._testMethodName
            destination.mkdir(parents=True, exist_ok=True)
            (destination / (name + '.json')).write_text(json.dumps(outcome, indent=2) + '\n')

    def test_recovery_retains_profile_bytes_history_and_native_references_in_a_disabled_candidate(self):
        before = self.configuration.path.read_bytes()
        result = self.recover(self.snapshot())
        self.assertEqual(result['status'], 'recovered', result)
        self.assertFalse(result['ownership_enabled'])
        self.assertEqual(result['profile'], str(self.destination / 'profile'))
        self.assertEqual(result['root'], str(self.destination / 'native/.claude'))
        self.assertEqual(self.configuration.path.read_bytes(), before)
        candidate = MemoryConfiguration(Path(result['profile']) / self.configuration.path.name).load()
        self.assertEqual(candidate['root'], result['root'])
        self.assertFalse(candidate['ownership_enabled'])
        self.assertFalse(candidate['sharing_enabled'])
        for name, data in self.fixture.sources.items():
            self.assertEqual((Path(result['profile']) / name).read_bytes(), data)
        with closing(sqlite3.connect(Path(result['profile']) / 'state.db')) as history:
            self.assertEqual(history.execute('SELECT body FROM sessions').fetchall(),
                             [('Synthetic committed profile history',)])
        recovered = NativeMemory(Path(result['root']))
        self.assertEqual(recovered.get(native_fixture.OWNER, self.fixture.saved['reference'])['content'],
                         'Synthetic coherent profile backup fact')
        receipt = json.loads(Path(result['recovery_manifest']).read_text())
        self.assertEqual(receipt['source_profile'], str(self.fixture.profile))
        self.assertEqual(receipt['destination'], str(self.destination))
        self.assertEqual(receipt['signature'], result['signature'])
        self.assertNotIn('Synthetic coherent profile backup fact', json.dumps(result))

    def test_recovery_rebinds_internal_and_native_links_to_the_candidate(self):
        profile = self.fixture.profile
        (profile / 'relative-memory').symlink_to('memories/MEMORY.md')
        (profile / 'absolute-memory').symlink_to(profile / 'memories/MEMORY.md')
        (profile / 'native-data').symlink_to(self.fixture.fixture.fixture.home / '.config/LIFEOS/USER')
        result = self.recover(self.snapshot())
        candidate = Path(result['profile'])
        for name in ('relative-memory', 'absolute-memory'):
            self.assertEqual((candidate / name).resolve(), candidate / 'memories/MEMORY.md')
        self.assertEqual((candidate / 'native-data').resolve(), self.destination / 'native/.config/LIFEOS/USER')
        self.assertEqual((candidate / 'native-data/MEMORY/STATE/memory-access.sqlite').resolve(),
                         NativeMemory(Path(result['root'])).database.resolve())

    def test_recovery_preserves_later_live_edits_facts_and_forget_decisions(self):
        signature = self.snapshot()
        later = self.fixture.fixture.fixture.remember('Synthetic live fact after profile snapshot', 'profile-recovery-later')
        memory = self.fixture.fixture.fixture.memory
        memory.forget(native_fixture.OWNER, self.fixture.saved['reference'], 'profile-recovery-later-forget')
        (self.fixture.profile / 'SOUL.md').write_text('# Synthetic later live identity\n')
        with closing(sqlite3.connect(self.fixture.database)) as history:
            history.execute("INSERT INTO sessions VALUES ('later','Synthetic later retained history')")
            history.commit()
        self.recover(signature)
        self.assertEqual(memory.get(native_fixture.OWNER, later['reference'])['content'], 'Synthetic live fact after profile snapshot')
        self.assertEqual(memory.get(native_fixture.OWNER, self.fixture.saved['reference'])['status'], 'conflict')
        self.assertEqual((self.fixture.profile / 'SOUL.md').read_text(), '# Synthetic later live identity\n')
        with closing(sqlite3.connect(self.fixture.database)) as history:
            self.assertEqual(history.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 2)

    def test_recovered_native_connector_uses_the_disabled_candidate_configuration(self):
        connector = self.fixture.fixture.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        connector.parent.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_rpc.py'),
                   '--configuration', str(self.configuration.path)]
        connector.write_text(json.dumps({'version': 1, 'command': command}))
        connector.chmod(0o600)
        original = connector.read_bytes()
        result = self.recover(self.snapshot())
        candidate = Path(result['root']) / 'LIFEOS/USER/CONFIG/memory-access.json'
        rebound = json.loads(candidate.read_text())
        self.assertEqual(rebound['command'][:3], command[:3])
        self.assertEqual(rebound['command'][3], str(Path(result['profile']) / self.configuration.path.name))
        self.assertEqual(connector.read_bytes(), original)
        receipt = json.loads(Path(result['recovery_manifest']).read_text())
        self.assertIn('native/.config/LIFEOS/USER/CONFIG/memory-access.json', receipt['rebound_files'])

    def test_recovery_refuses_an_unrecognized_native_connector_without_replacing_live_data(self):
        connector = self.fixture.fixture.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        connector.parent.mkdir(parents=True, exist_ok=True)
        connector.write_text(json.dumps({'version': 1, 'command': [sys.executable, '/unreviewed/agent.py']}))
        connector.chmod(0o600)
        signature = self.snapshot()
        with self.assertRaises(MemoryUnavailable):
            self.recover(signature)
        self.assertFalse(self.destination.exists())
        self.assertEqual(json.loads(connector.read_text())['command'], [sys.executable, '/unreviewed/agent.py'])

    def test_recovery_requires_owner_account_reviewed_signature_and_new_external_target(self):
        signature = self.snapshot()
        with self.assertRaises(PermissionError):
            recover(self.configuration, self.backup, signature, self.destination, account='chat-a:other')
        with self.assertRaises(MemoryUnavailable):
            self.recover('0' * 64)
        for destination in (self.backup / 'recovery', self.fixture.profile / 'recovery',
                            self.fixture.fixture.fixture.root / 'recovery',
                            self.fixture.fixture.fixture.home / '.config/LIFEOS/USER/recovery'):
            with self.subTest(destination=destination), self.assertRaises(MemoryUnavailable):
                recover(self.configuration, self.backup, signature, destination)
        self.destination.mkdir(parents=True)
        marker = self.destination / 'existing-owner-file'
        marker.write_text('Preserve the existing recovery target.\n')
        with self.assertRaises(MemoryUnavailable):
            self.recover(signature)
        self.assertEqual(marker.read_text(), 'Preserve the existing recovery target.\n')

    def test_recovery_works_when_original_history_and_native_data_are_unavailable(self):
        signature = self.snapshot()
        self.fixture.database.unlink()
        (self.fixture.profile / 'SOUL.md').unlink()
        user = self.fixture.fixture.fixture.home / '.config/LIFEOS/USER'
        user.rename(user.with_name('retained-original-data'))
        result = self.recover(signature)
        self.assertEqual(NativeMemory(Path(result['root'])).get(native_fixture.OWNER,
            self.fixture.saved['reference'])['content'], 'Synthetic coherent profile backup fact')
        self.assertFalse(self.fixture.database.exists())
        self.assertFalse(user.exists())

    def test_recovery_uses_captured_profile_tools_when_the_original_program_is_unavailable(self):
        tools = self.fixture.fixture.fixture.root / 'LIFEOS/TOOLS'
        original_tools = tools.resolve()
        captured = self.fixture.profile / 'LIFEOS/TOOLS'
        shutil.copytree(original_tools, captured)
        shutil.copytree(original_tools.parents[1] / 'hooks', self.fixture.profile / 'hooks')
        shutil.copytree(original_tools.parents[1] / 'node_modules', self.fixture.profile / 'node_modules')
        tools.unlink()
        tools.symlink_to(captured, target_is_directory=True)
        signature = self.snapshot()
        retained = captured.with_name('retained-original-tools')
        captured.rename(retained)
        result = self.recover(signature)
        restored_tools = Path(result['root']) / 'LIFEOS/TOOLS'
        self.assertEqual(restored_tools.resolve(), self.destination / 'profile/LIFEOS/TOOLS')
        self.assertEqual(result['program_tools'], str(self.destination / 'profile/LIFEOS/TOOLS'))
        self.assertEqual(NativeMemory(Path(result['root'])).get(native_fixture.OWNER,
            self.fixture.saved['reference'])['content'], 'Synthetic coherent profile backup fact')
        self.assertTrue(retained.is_dir())
        self.assertFalse(captured.exists())

    def test_recovered_actual_hermes_history_opens_and_continues_in_a_separate_process(self):
        from hermes_state import SessionDB
        self.fixture.database.unlink()
        warnings = io.StringIO()
        logger = logging.getLogger('hermes_state')
        handler = logging.StreamHandler(warnings)
        handler.setLevel(logging.WARNING)
        propagation = logger.propagate
        logger.addHandler(handler)
        logger.propagate = False
        try:
            with closing(SessionDB(self.fixture.database)) as history:
                history.create_session('recovered-hermes-session', 'discord', user_id='100', chat_id='200')
                history.append_message('recovered-hermes-session', 'user', content='Synthetic actual retained user message')
                history.append_message('recovered-hermes-session', 'assistant', content='Synthetic actual retained assistant reply')
                signature = self.snapshot()
        finally:
            logger.removeHandler(handler)
            logger.propagate = propagation
        if warnings.getvalue():
            self.assertEqual(len(warnings.getvalue().splitlines()), 1)
            self.assertIn('WAL-reset corruption bug', warnings.getvalue())
            self.assertIn('using journal_mode=DELETE', warnings.getvalue())
        result = self.recover(signature)
        script = '''import io,json,logging,sys
from contextlib import closing
from pathlib import Path
from hermes_state import SessionDB
warnings=io.StringIO()
logger=logging.getLogger('hermes_state')
handler=logging.StreamHandler(warnings)
handler.setLevel(logging.WARNING)
logger.addHandler(handler)
logger.propagate=False
with closing(SessionDB(Path(sys.argv[1]))) as history:
    before=history.get_messages_as_conversation('recovered-hermes-session')
    history.append_message('recovered-hermes-session','user',content='Synthetic recovered continuation')
    after=history.get_messages_as_conversation('recovered-hermes-session')
print(json.dumps({'before':before,'after':after,'warnings':warnings.getvalue()}))
'''
        continued = subprocess.run([sys.executable, '-W', 'error::ResourceWarning', '-c', script,
                                    str(Path(result['profile']) / 'state.db')],
            env=os.environ.copy(), capture_output=True, text=True, timeout=30)
        self.assertEqual(continued.returncode, 0, continued.stdout + continued.stderr)
        self.assertEqual(continued.stderr, '')
        outcome = json.loads(continued.stdout)
        self.assertEqual([message['content'] for message in outcome['before']],
            ['Synthetic actual retained user message', 'Synthetic actual retained assistant reply'])
        self.assertEqual([message['content'] for message in outcome['after']],
            ['Synthetic actual retained user message', 'Synthetic actual retained assistant reply', 'Synthetic recovered continuation'])
        if outcome['warnings']:
            self.assertEqual(len(outcome['warnings'].splitlines()), 1)
            self.assertIn('WAL-reset corruption bug', outcome['warnings'])
            self.assertIn('using journal_mode=DELETE', outcome['warnings'])
        with closing(sqlite3.connect(self.fixture.database)) as history:
            original_count = history.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
            self.assertEqual(original_count, 2)
        self.record('hermes-history', {'process_status': continued.returncode, 'outcome': outcome,
                                      'original_message_count': original_count})

    def test_process_exit_before_publication_retains_an_inert_candidate_and_original_files(self):
        signature = self.snapshot()
        before = self.configuration.path.read_bytes()
        script = '''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import lifeos_hook_bridge.profile_backup_recovery as recovery
s=json.loads(sys.stdin.read())
def trace(frame,event,argument):
    if frame.f_code.co_filename==recovery.__file__ and frame.f_code.co_name=='recover' and event=='line':
        stage=frame.f_locals.get('stage')
        if stage is not None and (stage/'.profile-recovery.json').is_file():
            os._exit(73)
    return trace
sys.settrace(trace)
recovery.recover(MemoryConfiguration(Path(s['configuration'])),Path(s['backup']),s['signature'],Path(s['destination']))
'''
        result = subprocess.run([sys.executable, '-W', 'error::ResourceWarning', '-c', script],
            input=json.dumps({'configuration': str(self.configuration.path), 'backup': str(self.backup),
                              'signature': signature, 'destination': str(self.destination)}),
            env=os.environ.copy(), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertFalse(self.destination.exists())
        stages = list(self.destination.parent.glob('.profile-recovery-*'))
        self.assertEqual(len(stages), 1)
        candidate = MemoryConfiguration(stages[0] / 'profile/lifeos-memory.json').load()
        self.assertFalse(candidate['ownership_enabled'])
        self.assertFalse(candidate['sharing_enabled'])
        self.assertEqual(self.configuration.path.read_bytes(), before)
        self.record('interruption', {'process_status': result.returncode, 'stage': str(stages[0]),
            'ownership_enabled': candidate['ownership_enabled'], 'sharing_enabled': candidate['sharing_enabled'],
            'source_configuration_digest': hashlib.sha256(before).hexdigest()})
        self.recover(signature)
        self.assertTrue(stages[0].is_dir())
