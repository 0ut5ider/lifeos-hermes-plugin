# ABOUTME: Verifies recovery of unpublished child admission through durable Hermes compression records.
# ABOUTME: Refuses reset parents, ambiguous children, redirected databases, and changed authority.
import json
import sqlite3
import unittest

from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError, MemoryRuntime
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_runtime as runtime_fixture
import test_memory_native as native_fixture


class MemoryLineageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.saved = self.fixture.fixture.remember('Synthetic recovered compression fact', 'lineage-original')
        self.fixture.admit()
        self.database = self.fixture.home / 'state.db'
        with sqlite3.connect(self.database) as connection:
            connection.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, parent_session_id TEXT, source TEXT, '
                               'user_id TEXT, chat_id TEXT, chat_type TEXT, thread_id TEXT, end_reason TEXT, ended_at REAL, model_config TEXT)')
            connection.executemany('INSERT INTO sessions (id,parent_session_id,source,user_id,chat_id,chat_type,thread_id,end_reason,ended_at) VALUES (?,?,?,?,?,?,?,?,?)', [
                ('session', None, 'chat-a', '100', '200', 'dm', None, 'compression', 1.0),
                ('child', 'session', 'chat-a', '100', '200', 'dm', None, None, None)])
        connection.close()
        self.database.chmod(0o600)
        self.before = self.fixture.runtime.state_path.read_bytes()
        self.fixture.runtime.clear()

    def change(self, sql, parameters=()):
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(sql, parameters)
            connection.commit()
        finally:
            connection.close()

    def resume(self):
        runtime = MemoryRuntime(self.fixture.path)
        runtime.admit(self.fixture.metadata(session='child'), **self.fixture.route, is_first_turn=False,
                      user_message='Synthetic recovered continuation')
        return runtime

    def refused(self):
        with self.assertRaises(MemoryAdmissionError):
            self.resume()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), self.before)
        self.assertIsNone(self.fixture.runtime.context())

    def test_recovery_records_only_the_verified_compression_child_and_preserves_parent(self):
        runtime = self.resume()
        states = json.loads(runtime.state_path.read_text())
        self.assertEqual(states['session'], json.loads(self.before)['session'])
        self.assertEqual(states['child']['compression_parent'], 'session')
        runtime.check_call(request={'messages': [{'role': 'user', 'content': 'Synthetic recovered continuation'}]},
                           **self.fixture.route, session_id='child')

    def test_recovery_preserves_fact_retirement_for_foreground_history_repair(self):
        self.fixture.fixture.memory.forget(native_fixture.OWNER, self.saved['reference'], 'lineage-forget')
        runtime = self.resume()
        with self.assertRaisesRegex(MemoryAdmissionError, 'invalidated memory context'):
            runtime.check_call(request={'messages': [{'role': 'user', 'content': 'Synthetic generated title'}]},
                               **self.fixture.route, session_id='child', aux_task='title_generation')
        sent = []
        runtime.project_call(request={'messages': [{'role': 'assistant', 'content': 'Synthetic recovered compression fact'},
            {'role': 'user', 'content': 'Synthetic recovered continuation'}]}, next_call=sent.append,
            **self.fixture.route, session_id='child')
        self.assertEqual(len(sent), 1)
        self.assertNotIn('Synthetic recovered compression fact', json.dumps(sent))

    def test_recovery_refuses_an_ordinary_reset_parent(self):
        self.change("UPDATE sessions SET end_reason='reset' WHERE id='session'")
        self.refused()

    def test_recovery_refuses_a_live_parent_or_ended_child(self):
        self.change("UPDATE sessions SET ended_at=NULL WHERE id='session'")
        self.refused()
        self.change("UPDATE sessions SET ended_at=1 WHERE id='session'")
        self.change("UPDATE sessions SET ended_at=2, end_reason='reset' WHERE id='child'")
        self.refused()

    def test_recovery_refuses_multiple_live_children(self):
        self.change("INSERT INTO sessions VALUES ('other', 'session', 'chat-a', '100', '200', 'dm', NULL, NULL, NULL, NULL)")
        self.refused()

    def test_recovery_ignores_a_delegated_sibling_using_the_native_continuation_rule(self):
        self.change("INSERT INTO sessions VALUES ('delegate', 'session', 'tool', NULL, NULL, NULL, NULL, NULL, NULL, ?)",
                    (json.dumps({'_delegate_from': 'session'}),))
        runtime = self.resume()
        self.assertEqual(runtime.context().session_id, 'child')

    def test_recovery_refuses_a_branch_or_reset_child(self):
        for marker in ('_branched_from', '_delegate_from', '_reset_from'):
            with self.subTest(marker=marker):
                self.change("UPDATE sessions SET model_config=? WHERE id='child'", (json.dumps({marker: 'session'}),))
                self.refused()

    def test_recovery_requires_the_parents_verified_memory_record(self):
        self.fixture.runtime.state_path.write_text('{}\n')
        self.before = self.fixture.runtime.state_path.read_bytes()
        self.refused()

    def test_recovery_refuses_a_changed_installed_prompt(self):
        (self.fixture.home / 'SOUL.md').write_text('# Synthetic changed compression identity\n')
        self.refused()

    def test_recovery_requires_the_recorded_proposal_policy(self):
        states = json.loads(self.before)
        states['session'].pop('proposal_generation')
        self.fixture.runtime.state_path.write_text(json.dumps(states))
        self.before = self.fixture.runtime.state_path.read_bytes()
        self.refused()

    def test_recovery_refuses_a_changed_native_author_or_destination(self):
        self.change("UPDATE sessions SET user_id='other' WHERE id='child'")
        self.refused()
        self.change("UPDATE sessions SET user_id='100', chat_id='other' WHERE id='child'")
        self.refused()

    def test_recovery_refuses_unknown_or_missing_parent_admission(self):
        self.change("UPDATE sessions SET parent_session_id='unknown' WHERE id='child'")
        self.refused()

    def test_recovery_refuses_changed_permissions(self):
        self.fixture.configuration['destinations']['chat-a:200']['write'] = []
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.refused()

    def test_recovery_refuses_redirected_or_public_database(self):
        self.database.chmod(0o644)
        self.refused()
        self.database.chmod(0o600)
        target = self.database.with_name('moved-state.db')
        self.database.rename(target)
        self.database.symlink_to(target)
        self.refused()

    def test_recovery_refuses_missing_or_invalid_database(self):
        self.database.unlink()
        self.refused()
        self.database.write_bytes(b'Synthetic invalid session database')
        self.database.chmod(0o600)
        self.refused()
