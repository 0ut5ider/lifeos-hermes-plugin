# ABOUTME: Exercises the Pulse core-file editor through real native and authenticated owner HTTP listeners.
# ABOUTME: Checks owner-only disclosure, reviewed saves, sealed files, and preservation of later edits.
import os
from pathlib import Path
import unittest
import httpx
import test_memory_pulse_relay as relay_fixture


class MemoryCoreEditorTests(unittest.TestCase):
    native_module = 'hermes.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def seed(self):
        path = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# SyntheticCoreEditorIdentity\nSynthetic owner identity\n')
        return path

    def read(self, client, identifier='principal-identity'):
        return client.get(self.native + '/api/hermes/file/' + identifier)

    def test_anonymous_file_read_and_write_refuse_before_disclosure_or_mutation(self):
        path = self.seed()
        before = path.read_bytes()
        response = httpx.get(self.native + '/api/hermes/file/principal-identity')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertNotIn('SyntheticCoreEditorIdentity', response.text)
        response = httpx.put(self.native + '/api/hermes/file/principal-identity', json={'content': '# Unauthorized edit', 'reference': '0' * 64, 'request_id': 'synthetic-unauthorized-core-edit'})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(path.read_bytes(), before)

    def test_current_owner_read_preserves_body_and_supplies_review_reference(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            response = self.read(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['content'], path.read_text())
            self.assertEqual(response.json()['meta']['id'], 'principal-identity')
            self.assertRegex(response.json()['reference'], r'^[0-9a-f]{64}$')
            self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_current_reviewed_save_is_private_and_idempotent(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client)
            self.assertEqual(read.status_code, 200, read.text)
            body = {'content': '# SyntheticCurrentCoreEdit\n', 'reference': read.json()['reference'],
                'request_id': 'synthetic-core-editor-save'}
            saved = client.put(self.native + '/api/hermes/file/principal-identity', json=body)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertTrue(saved.json()['ok'])
            self.assertEqual(path.read_text(), body['content'])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            repeated = client.put(self.native + '/api/hermes/file/principal-identity', json=body)
            self.assertEqual(repeated.status_code, 200, repeated.text)
            self.assertEqual(repeated.json(), saved.json())

    def test_later_owner_edit_refuses_stale_save(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client)
            self.assertEqual(read.status_code, 200, read.text)
            reference = read.json()['reference']
            path.write_text('# SyntheticLaterCoreEdit\n')
            before = path.read_bytes(), path.stat().st_mtime_ns
            response = client.put(self.native + '/api/hermes/file/principal-identity',
                json={'content': '# Stale overwrite', 'reference': reference, 'request_id': 'synthetic-stale-core-edit'})
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_revoked_owner_cannot_read_profile_details(self):
        self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = self.read(client)
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('SyntheticCoreEditorIdentity', response.text)

    def test_current_owner_cannot_read_or_edit_credential_material(self):
        with httpx.Client(timeout=60) as client:
            self.login(client)
            for method in ('GET', 'PUT'):
                response = client.request(method, self.native + '/api/hermes/file/hermes-env',
                    json={'content': 'Synthetic edit', 'reference': '0' * 64, 'request_id': 'synthetic-sealed-core-edit'} if method == 'PUT' else None)
                self.assertEqual(response.status_code, 403, response.text)
                self.assertNotIn('synthetic-password', response.text)


if __name__ == '__main__':
    unittest.main()
