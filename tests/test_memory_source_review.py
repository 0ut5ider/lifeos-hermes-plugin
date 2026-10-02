# ABOUTME: Tests owner review of exact native system and identity sources after retirement.
# ABOUTME: Verifies that review preserves native formatting without admitting excluded facts.
from dataclasses import replace
import os
import shutil
import unittest

from lifeos_hook_bridge.memory_sources import read_markdown
from test_memory_native import OWNER
import test_memory_prompt as prompt_fixture


class MemorySourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = prompt_fixture.MemoryPromptTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.root = self.fixture.root
        self.preferences = self.fixture.preferences()
        self.paths = ['LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
            'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
            'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
            'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', 'LIFEOS/USER/PROJECTS.md',
            'skills/SyntheticSkill/SKILL.md']

    def forget(self, content='RULE: SyntheticRetiredUnrelatedFact', identifier='retired'):
        saved = self.memory.remember(OWNER, category='principal', content=content,
            title='', project='', request_id=identifier)
        self.assertEqual(saved['status'], 'committed', saved)
        return self.memory.forget(OWNER, saved['reference'], identifier + '-forgotten')

    def preview(self, paths=None):
        return self.preferences.preview_sources(self.paths if paths is None else paths, account='dashboard:owner')

    def approve(self, snapshot, paths=None):
        return self.preferences.approve_sources({'paths': self.paths if paths is None else paths,
            'signature': snapshot['signature']}, account='dashboard:owner')

    def test_review_restores_safe_old_prompt_without_changing_source_files(self):
        self.forget()
        self.assertFalse(self.fixture.native()['ok'])
        before = {path: ((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns) for path in self.paths}
        snapshot = self.preview()
        self.assertTrue(all(row['accepted'] for row in snapshot['sources']), snapshot)
        self.assertEqual(self.approve(snapshot)['status'], 'committed')
        self.assertEqual(self.fixture.native(), self.fixture.native(managed=False))
        for path, state in before.items():
            self.assertEqual(((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns), state)
        self.assertEqual(self.fixture.mount().returncode, 0)
        self.assertEqual(self.approve(snapshot)['status'], 'unchanged')
        with self.memory._transaction() as connection:
            rows = [dict(row) for row in connection.execute('SELECT * FROM source_reviews')]
        self.assertEqual(len(rows), len(self.paths))
        self.assertNotIn('SyntheticSafetyDoctrine', str(rows))
        self.assertFalse(self.fixture.fixture.configuration.load().get('ownership_enabled', False))

    def test_review_cannot_admit_a_known_retired_claim_or_private_body(self):
        self.forget()
        for body in ('RULE: SyntheticRetiredUnrelatedFact', '<private>SyntheticPrivateBody</private>'):
            with self.subTest(body=body):
                self.fixture.write(self.paths[0], body)
                snapshot = self.preview([self.paths[0]])
                self.assertFalse(snapshot['sources'][0]['accepted'], snapshot)
                self.assertNotIn(body, str(snapshot))
                self.assertEqual(self.approve(snapshot, [self.paths[0]])['status'], 'rejected')
                self.assertFalse(read_markdown(self.memory, OWNER, [str(self.root / self.paths[0])]))

    def test_changed_sources_and_new_retirement_invalidate_review(self):
        self.forget()
        snapshot = self.preview()
        self.assertEqual(self.approve(snapshot)['status'], 'committed')
        timestamp = (self.root / self.paths[0]).stat().st_mtime_ns
        self.fixture.write(self.paths[0], '# SyntheticChangedConstitution\n')
        os.utime(self.root / self.paths[0], ns=(timestamp, timestamp))
        self.assertEqual(self.approve(snapshot)['status'], 'conflict')
        self.assertFalse(self.fixture.native()['ok'])
        fresh = self.preview()
        self.assertEqual(self.approve(fresh)['status'], 'committed')
        self.assertTrue(self.fixture.native()['ok'])
        self.forget('RULE: SyntheticLaterRetiredFact', 'later')
        self.assertEqual(self.approve(fresh)['status'], 'conflict')
        self.assertFalse(self.fixture.native()['ok'])

    def test_non_owner_cannot_preview_or_approve(self):
        with self.assertRaises(PermissionError):
            self.preferences.preview_sources(self.paths, account='dashboard:other')
        with self.assertRaises(PermissionError):
            self.preferences.approve_sources({'paths': self.paths, 'signature': 'a' * 64}, account='dashboard:other')

    def test_review_does_not_grant_restricted_recall(self):
        self.forget()
        self.assertEqual(self.approve(self.preview())['status'], 'committed')
        with self.assertRaises(RuntimeError):
            read_markdown(self.memory, replace(OWNER, read=('project',), projects=('lab',)),
                [str(self.root / self.paths[0])])
        self.fixture.fixture.configuration.update(
            lambda value: value['destinations']['chat-a:200'].update(read=['project']))
        self.assertFalse(self.fixture.native()['ok'])

    def test_review_refuses_history_traversal_duplicate_and_redirected_paths(self):
        self.fixture.write('LIFEOS/MEMORY/LEARNING/synthetic.md', 'Synthetic retained history')
        for paths in (['LIFEOS/MEMORY/LEARNING/synthetic.md'], ['../outside.md'],
                      [self.paths[0], self.paths[0]], [str(self.root / self.paths[0])], []):
            with self.subTest(paths=paths), self.assertRaises((ValueError, RuntimeError)):
                self.preview(paths)
        target = self.root / self.paths[0]
        target.unlink()
        target.symlink_to(self.fixture.skill)
        with self.assertRaises(RuntimeError):
            self.preview([self.paths[0]])

    def test_native_private_validation_still_runs_after_review(self):
        self.forget()
        self.assertEqual(self.approve(self.preview())['status'], 'committed')
        self.fixture.skill.write_text('<private>SyntheticLaterPrivateSkill</private>')
        rendered = self.fixture.native()
        self.assertTrue(rendered['ok'], rendered)
        self.assertNotIn('SyntheticLaterPrivateSkill', str(rendered))

    def test_touching_an_unreviewed_source_does_not_reuse_another_approval(self):
        self.forget()
        self.assertEqual(self.approve(self.preview([self.paths[0]]), [self.paths[0]])['status'], 'committed')
        identity = self.root / self.paths[1]
        old = identity.stat().st_mtime_ns
        os.utime(identity, ns=(old, old))
        self.assertEqual(read_markdown(self.memory, OWNER, [str(identity)]), [])

    def test_changed_configuration_invalidates_the_preview(self):
        snapshot = self.preview()
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertEqual(self.approve(snapshot)['status'], 'conflict')
        with self.memory._transaction() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM source_reviews').fetchone()[0], 0)

    def test_copied_metadata_cannot_review_a_different_installation(self):
        self.forget()
        self.assertEqual(self.approve(self.preview())['status'], 'committed')
        other = prompt_fixture.MemoryPromptTests()
        other.setUp()
        self.addCleanup(other.doCleanups)
        other.memory.database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.memory.database, other.memory.database)
        for relative in self.paths:
            timestamp = (self.root / relative).stat().st_mtime_ns
            os.utime(other.root / relative, ns=(timestamp, timestamp))
        self.assertFalse(other.native()['ok'])
        self.assertEqual(read_markdown(self.memory, replace(OWNER, principal='other-owner'),
            [str(self.root / self.paths[0])]), [])

    def test_schema_upgrade_preserves_existing_fact_and_operation_metadata(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticPreservedFact',
            title='', project='', request_id='schema-preserve')
        with self.memory._transaction() as connection:
            connection.execute('DROP TABLE source_reviews')
            connection.execute('PRAGMA user_version=3')
            records = [dict(row) for row in connection.execute('SELECT * FROM records')]
            operations = [dict(row) for row in connection.execute('SELECT * FROM operations')]
        self.preview()
        with self.memory._transaction() as connection:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 4)
            self.assertEqual([dict(row) for row in connection.execute('SELECT * FROM records')], records)
            self.assertEqual([dict(row) for row in connection.execute('SELECT * FROM operations')], operations)
        self.assertIn('SyntheticPreservedFact', self.memory.get(OWNER, saved['reference'])['content'])

    def test_revocation_during_source_validation_prevents_approval(self):
        from unittest.mock import patch
        from lifeos_hook_bridge.memory_access import NativeMemory
        snapshot = self.preview()
        original = NativeMemory._native
        def revoke_owner(memory, action, **values):
            result = original(memory, action, **values)
            if action == 'validate_source_batch':
                self.fixture.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:owner'))
            return result
        with patch.object(NativeMemory, '_native', revoke_owner), self.assertRaises(PermissionError):
            self.approve(snapshot)
        with self.memory._transaction() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM source_reviews').fetchone()[0], 0)

    def test_model_context_cannot_approve_source_review(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        result = MemoryService(self.fixture.fixture.configuration).native(self.fixture.fixture.context,
            'approve_sources', {'paths': self.paths, 'signature': self.preview()['signature']})
        self.assertFalse(result['ok'], result)
        with self.memory._transaction() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM source_reviews').fetchone()[0], 0)

    def test_authenticated_http_reviews_sources_and_refuses_unbound_accounts(self):
        import warnings
        from pathlib import Path
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            import test_memory_pulse_auth as http_fixture
        self.assertTrue(all(issubclass(warning.category, DeprecationWarning) and
            'BlockingPortal alias is deprecated' in str(warning.message) for warning in recorded))
        http = http_fixture.MemoryPulseAuthTests()
        http.setUp()
        self.addCleanup(http.doCleanups)
        root = Path(http.configuration.load()['root'])
        for relative in self.paths:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text((self.root / relative).read_text())
        http.login()
        client = http.client
        endpoint = '/api/plugins/lifeos-hook-bridge/memory/sources'
        response = client.post(endpoint + '/preview', json={'paths': self.paths})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('no-store', response.headers['Cache-Control'])
        snapshot = response.json()
        response = client.post(endpoint, json={'paths': self.paths, 'signature': snapshot['signature']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'committed')
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertEqual(client.post(endpoint, json={'paths': self.paths,
            'signature': snapshot['signature'], 'reviewed': True}).status_code, 409)
        http.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
        response = client.post(endpoint + '/preview', json={'paths': self.paths})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('SyntheticSafetyDoctrine', response.text)
        client.cookies.clear()
        response = client.post(endpoint + '/preview', json={'paths': self.paths})
        self.assertEqual(response.status_code, 401)
        self.assertIn('no-store', response.headers['Cache-Control'])


if __name__ == '__main__':
    unittest.main()
