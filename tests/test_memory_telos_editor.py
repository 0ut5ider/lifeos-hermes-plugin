# ABOUTME: Exercises the native TELOS editor through actual authenticated owner HTTP requests.
# ABOUTME: Checks native file fields, current edit references, private publication, and refused callers.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryTelosEditorTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login
    original = life_fixture.MemoryLifeRelayTests.original

    def seed(self):
        path = self.root / 'LIFEOS/USER/TELOS/GOALS.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# SyntheticEditableTelosGoal\nSynthetic current goal\n')
        return path

    def read(self, client, name='GOALS.md'):
        return client.get(self.native + '/api/telos/file', params={'name': name})

    def test_current_owner_read_preserves_native_file_fields(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = self.read(client)
            self.assertEqual(response.status_code, 200, response.text)
            expected = self.original('/api/telos/file?name=GOALS.md')
            self.assertEqual({key: response.json()[key] for key in expected}, expected)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertRegex(response.json()['reference'], r'^[0-9a-f]{64}$')

    def test_anonymous_read_and_write_refuse_before_disclosing_or_changing_file(self):
        path = self.seed()
        before = path.read_bytes()
        response = httpx.get(self.native + '/api/telos/file?name=GOALS.md')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertNotIn('SyntheticEditableTelosGoal', response.text)
        response = httpx.put(self.native + '/api/telos/file', json={'name': 'GOALS.md',
            'content': 'Synthetic unauthorized edit', 'reference': '0' * 64, 'request_id': 'synthetic-denied-edit'})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(path.read_bytes(), before)

    def test_owner_saves_only_the_current_reviewed_reference_privately(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            before = self.read(client).json()
            request = {'name': 'GOALS.md', 'content': '# SyntheticOwnerEditedGoal\r\n',
                'reference': before['reference'], 'request_id': 'synthetic-owner-edit'}
            response = client.put(self.native + '/api/telos/file', json=request)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['ok'])
            self.assertEqual(path.read_bytes(), request['content'].encode())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            repeated = client.put(self.native + '/api/telos/file', json=request)
            self.assertEqual(repeated.status_code, 200, repeated.text)
            self.assertEqual(repeated.json(), response.json())

    def test_private_source_is_withheld_without_changing_its_bytes(self):
        path = self.seed()
        path.write_text('# SyntheticPrivateEditor\n<private>Synthetic withheld editor body</private>\n')
        before = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = self.read(client)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticPrivateEditor', response.text)
            self.assertEqual(path.read_bytes(), before)

    def test_missing_file_read_can_create_one_declared_file(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = self.read(client, 'NEW_TEST.md')
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual((body['content'], body['mtime'], body['missing']), ('', None, True))
            response = client.put(self.native + '/api/telos/file', json={'name': 'NEW_TEST.md',
                'content': '# SyntheticNewEditorFile\n', 'reference': body['reference'],
                'request_id': 'synthetic-new-editor-file'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual((self.root / 'LIFEOS/USER/TELOS/NEW_TEST.md').read_text(), '# SyntheticNewEditorFile\n')

    def test_save_preserves_a_later_owner_edit_and_requires_a_fresh_reference(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            reference = self.read(client).json()['reference']
            path.write_text('# SyntheticConcurrentOwnerEdit\n')
            before = path.read_bytes(), path.stat().st_mtime_ns
            response = client.put(self.native + '/api/telos/file', json={'name': 'GOALS.md',
                'content': '# SyntheticStaleEditorSave\n', 'reference': reference,
                'request_id': 'synthetic-conflicting-editor-save'})
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_save_without_a_current_reference_does_not_write(self):
        path = self.seed()
        before = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.put(self.native + '/api/telos/file', json={'name': 'GOALS.md',
                'content': '# SyntheticUnreviewedEditorSave\n'})
            self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual(path.read_bytes(), before)

    def test_private_save_preserves_the_current_file(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            reference = self.read(client).json()['reference']
            before = path.read_bytes()
            response = client.put(self.native + '/api/telos/file', json={'name': 'GOALS.md',
                'content': '<private>SyntheticPrivateEditorSave</private>', 'reference': reference,
                'request_id': 'synthetic-private-editor-save'})
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(path.read_bytes(), before)

    def test_current_credentials_selectors_origin_and_method_are_required(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, query, headers, expected in (
                ('GET', '?name=GOALS.md', {'Authorization': 'Bearer synthetic-invalid'}, 401),
                ('GET', '?name=GOALS.md', {'Origin': 'https://synthetic.invalid'}, 403),
                ('GET', '?name=GOALS.md&name=MISSION.md', {}, 400),
                ('GET', '?name=GOALS.md&owner=other', {}, 400),
                ('GET', '?name=../GOALS.md', {}, 400), ('GET', '?name=unknown.md', {}, 400),
                ('POST', '', {}, 405)):
                with self.subTest(method=method, query=query):
                    response = client.request(method, self.native + '/api/telos/file' + query, headers=headers)
                    self.assertEqual(response.status_code, expected, response.text)
                    self.assertNotIn('SyntheticEditableTelosGoal', response.text)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            response = self.read(client)
            self.assertEqual(response.status_code, 403, response.text)
            self.assertEqual(path.read_text(), '# SyntheticEditableTelosGoal\nSynthetic current goal\n')

    def test_redirected_hardlinked_and_oversize_sources_cannot_open_in_the_editor(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            external = self.fixture.home / 'synthetic-external-editor.md'
            path.rename(external)
            path.symlink_to(external)
            self.assertEqual(self.read(client).status_code, 503)
            path.unlink()
            path.write_bytes(external.read_bytes())
            os.link(path, self.fixture.home / 'synthetic-hardlinked-editor.md')
            self.assertEqual(self.read(client).status_code, 503)
            path.unlink()
            path.write_text('SyntheticOversizeEditorSource' * 12000)
            self.assertEqual(self.read(client).status_code, 503)

    def test_completed_save_retry_preserves_later_edits(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            request = {'name': 'GOALS.md', 'content': '# SyntheticCommittedEditorSave\n',
                'reference': self.read(client).json()['reference'], 'request_id': 'synthetic-editor-later-change'}
            response = client.put(self.native + '/api/telos/file', json=request)
            self.assertEqual(response.status_code, 200, response.text)
            path.write_text('# SyntheticLaterOwnerEditorSave\n')
            before = path.read_bytes(), path.stat().st_mtime_ns
            response = client.put(self.native + '/api/telos/file', json=request)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_retirement_refuses_retained_body_and_safe_source_review_can_restore_unrelated_text(self):
        path = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: SyntheticUnrelatedEditorRetirement',
            title='', project='', request_id='synthetic-editor-retirement-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-editor-retirement')
        before = path.read_bytes(), path.stat().st_mtime_ns
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(self.read(client).status_code, 503)
            endpoint = self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/sources'
            paths = ['LIFEOS/USER/TELOS/GOALS.md']
            preview = client.post(endpoint + '/preview', json={'paths': paths})
            self.assertEqual(preview.status_code, 200, preview.text)
            approved = client.post(endpoint, json={'paths': paths, 'signature': preview.json()['signature']})
            self.assertEqual(approved.json()['status'], 'committed', approved.text)
            response = self.read(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('SyntheticEditableTelosGoal', response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_actual_process_interruption_recovers_prior_file_and_permissions(self):
        path = self.seed()
        path.chmod(0o640)
        before = path.read_bytes(), path.stat().st_mode & 0o777
        with httpx.Client(timeout=30) as client:
            self.login(client)
            request = {'name': 'GOALS.md', 'content': '# SyntheticInterruptedEditorSave\n',
                'reference': self.read(client).json()['reference'], 'request_id': 'synthetic-editor-interrupted'}
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_telos_edit_process.py')),
                str(self.fixture.configuration.path), json.dumps(request), 'interrupt'],
                capture_output=True, text=True, timeout=40,
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
            self.assertEqual(result.returncode, 86, result.stderr)
            self.assertEqual(result.stdout + result.stderr, '')
            response = self.read(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mode & 0o777), before)

    def test_authority_change_after_actual_source_read_refuses_before_publication(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            request = {'name': 'GOALS.md', 'content': '# SyntheticRevokedEditorSave\n',
                'reference': self.read(client).json()['reference'], 'request_id': 'synthetic-editor-revoked'}
            before = path.read_bytes(), path.stat().st_mtime_ns
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_telos_edit_process.py')),
                str(self.fixture.configuration.path), json.dumps(request), 'revoke'],
                capture_output=True, text=True, timeout=40,
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout), {'observed': True, 'withheld': True})
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)


if __name__ == '__main__':
    unittest.main()
