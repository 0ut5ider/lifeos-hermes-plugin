# ABOUTME: Exercises the Pulse core-file editor through real native and authenticated owner HTTP listeners.
# ABOUTME: Checks owner-only disclosure, reviewed saves, sealed files, and preservation of later edits.
import os
import shutil
import json
import time
import subprocess
import sys
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

    def seed_programs(self):
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/HERMES'
        target = self.root / 'LIFEOS/HERMES'
        shutil.copytree(source, target)
        return target

    def test_all_native_program_files_preserve_their_exact_public_bodies(self):
        from lifeos_hook_bridge.memory_core_file import CODE_FILES
        programs = self.seed_programs()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            for identifier, relative in CODE_FILES.items():
                with self.subTest(identifier=identifier):
                    response = self.read(client, identifier)
                    if (programs / relative).is_file():
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['content'], (programs / relative).read_text())
                    else:
                        self.assertEqual(response.status_code, 404, response.text)
                        self.assertFalse(response.json()['meta']['exists'])

    def test_profile_configuration_and_cron_definitions_use_reviewed_saves(self):
        profile = self.fixture.configuration.path.parent
        (profile / 'cron').mkdir()
        for identifier, relative, before, after in (
            ('config', 'config.yaml', 'model: synthetic-private-model\n', 'model: synthetic-new-private-model\n'),
            ('cron-jobs', 'cron/jobs.json', '{"jobs": []}\n', '{"jobs": [], "version": 1}\n')):
            with self.subTest(identifier=identifier):
                path = profile / relative
                path.write_text(before)
                with httpx.Client(timeout=60) as client:
                    self.login(client)
                    read = self.read(client, identifier)
                    self.assertEqual(read.status_code, 200, read.text)
                    response = client.put(self.native + '/api/hermes/file/' + identifier,
                        json={'content': after, 'reference': read.json()['reference'], 'request_id': 'synthetic-core-' + identifier})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(path.read_text(), after)

    def test_program_save_refuses_credentials_and_records_release_change(self):
        programs = self.seed_programs()
        path = programs / 'Health.ts'
        before = path.read_bytes()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client, 'health')
            self.assertEqual(read.status_code, 200, read.text)
            denied = client.put(self.native + '/api/hermes/file/health', json={
                'content': 'export const token = "sk-' + 'a' * 40 + '";\n',
                'reference': read.json()['reference'], 'request_id': 'synthetic-code-containment'})
            self.assertEqual(denied.status_code, 422, denied.text)
            self.assertEqual(path.read_bytes(), before)
            edited = before.decode() + '\n// Synthetic owner program edit\n'
            saved = client.put(self.native + '/api/hermes/file/health', json={'content': edited,
                'reference': read.json()['reference'], 'request_id': 'synthetic-core-program-edit'})
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertTrue(saved.json()['releaseModified'])
            self.assertEqual(path.read_text(), edited)

    def test_generated_files_refuse_save_and_registered_facts_remain_bound(self):
        profile = self.fixture.configuration.path.parent
        (profile / 'SOUL.md').write_text('# Synthetic generated soul\n')
        with httpx.Client(timeout=60) as client:
            self.login(client)
            for identifier in ('soul', 'principal-memory'):
                with self.subTest(identifier=identifier):
                    read = self.read(client, identifier)
                    self.assertEqual(read.status_code, 200, read.text)
                    self.assertFalse(read.json()['meta']['editable'])
                    response = client.put(self.native + '/api/hermes/file/' + identifier,
                        json={'content': '# Synthetic raw replacement', 'reference': read.json()['reference'],
                            'request_id': 'synthetic-forbidden-core-' + identifier})
                    self.assertEqual(response.status_code, 409, response.text)
            found = client.post(self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/review',
                json={'tool': 'lifeos_memory_search', 'arguments': {'query': 'authenticated PULSE'}})
            self.assertEqual(found.status_code, 200, found.text)
            self.assertTrue(found.json()['results'])

    def test_private_and_retired_source_bodies_are_withheld(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            path.write_text('<private>Synthetic withheld core identity</private>\n')
            response = self.read(client)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('Synthetic withheld core identity', response.text)

    def test_forgotten_claim_cannot_return_through_core_reads_or_saves(self):
        from lifeos_hook_bridge.memory_access import NativeMemory
        from test_memory_native import OWNER
        path = self.seed()
        memory = NativeMemory(self.root, profile=self.fixture.configuration.path.parent)
        claim = 'The synthetic retired pipeline uses violet envelopes.'
        saved = memory.remember(OWNER, category='project', content=claim, title='Synthetic retired pipeline',
            project='lab', request_id='core-retirement-remember')
        self.assertEqual(saved['status'], 'committed')
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'core-retirement-forget')['status'], 'committed')
        with httpx.Client(timeout=60) as client:
            self.login(client)
            reference = self.read(client).json()['reference']
            before = path.read_bytes()
            response = client.put(self.native + '/api/hermes/file/principal-identity',
                json={'content': claim, 'reference': reference, 'request_id': 'core-retirement-refused-save'})
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn(claim, response.text)
            self.assertEqual(path.read_bytes(), before)
            path.write_text(claim)
            response = self.read(client)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn(claim, response.text)

    def test_redirected_and_hardlinked_profile_sources_are_withheld(self):
        profile = self.fixture.configuration.path.parent
        external = self.fixture.home / 'synthetic-external-core-config'
        external.write_text('model: synthetic-external\n')
        path = profile / 'config.yaml'
        path.symlink_to(external)
        with httpx.Client(timeout=60) as client:
            self.login(client)
            for kind in ('symlink', 'hardlink'):
                with self.subTest(kind=kind):
                    if kind == 'hardlink':
                        path.unlink()
                        os.link(external, path)
                    response = self.read(client, 'config')
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertNotIn('synthetic-external', response.text)

    def test_overview_retains_registry_and_native_gateway_health(self):
        self.seed()
        self.seed_programs()
        profile = self.fixture.configuration.path.parent
        (profile / 'gateway_state.json').write_text(json.dumps({'pid': os.getpid(), 'active_agents': 2,
            'updated_at': '2026-10-14T00:00:00Z', 'platforms': {'discord': {'state': 'connected'}}}))
        (profile / 'gateway-starts.log').write_text(str(time.time()) + '\n')
        with httpx.Client(timeout=120) as client:
            self.login(client)
            response = client.get(self.native + '/api/hermes')
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(len(body['files']), 24)
            self.assertEqual(body['health']['pid'], os.getpid())
            self.assertEqual(body['health']['activeAgents'], 2)
            self.assertEqual(body['health']['platforms'][0]['state'], 'connected')
            self.assertEqual(body['health']['recentStarts'], 1)
            self.assertTrue(body['mount']['probed'])

    def test_guard_analysis_keeps_actual_native_counts_and_refuses_anonymous_access(self):
        self.seed_programs()
        profile = self.fixture.configuration.path.parent
        folder = profile / 'plugins/lifeos'
        folder.mkdir(parents=True)
        row = {'ts': '2099-01-01T00:00:00Z', 'tool': 'terminal', 'target': 'synthetic target',
            'reason': "deny rule 'synthetic-example'"}
        (folder / 'blocked.jsonl').write_text(json.dumps(row) + '\n')
        response = httpx.get(self.native + '/api/hermes/log-analysis?days=14')
        self.assertEqual(response.status_code, 401, response.text)
        with httpx.Client(timeout=60) as client:
            self.login(client)
            response = client.get(self.native + '/api/hermes/log-analysis?days=14')
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body['totalBlocks'], 1)
            self.assertEqual(body['byClass'], {'deny-rule': 1})
            self.assertEqual(body['topRules'][0]['rule'], 'synthetic-example')

    def interrupt_save(self, identifier, path, client):
        read = self.read(client, identifier)
        self.assertEqual(read.status_code, 200, read.text)
        request = {'identifier': identifier, 'content': 'model: synthetic-interrupted\n' if identifier == 'config' else '# Synthetic interrupted core source\n',
            'reference': read.json()['reference'], 'request_id': 'synthetic-core-interruption-' + identifier}
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_core_edit_process.py')),
            str(self.fixture.configuration.path), json.dumps(request), 'interrupt'], capture_output=True, text=True, timeout=60,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 86, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertEqual(path.read_text(), request['content'])
        return request

    def test_real_process_interruption_recovers_source_bytes_and_permissions(self):
        path = self.seed()
        path.chmod(0o640)
        before = path.read_bytes(), path.stat().st_mode & 0o777
        with httpx.Client(timeout=60) as client:
            self.login(client)
            self.interrupt_save('principal-identity', path, client)
            response = self.read(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mode & 0o777), before)

    def test_interrupted_profile_save_recovers_through_the_other_owner_memory_route(self):
        profile = self.fixture.configuration.path.parent
        (self.fixture.home / '.hermes').symlink_to(profile, target_is_directory=True)
        path = profile / 'config.yaml'
        path.write_text('model: synthetic-original\n')
        path.chmod(0o640)
        before = path.read_bytes(), path.stat().st_mode & 0o777
        with httpx.Client(timeout=60) as client:
            self.login(client)
            self.interrupt_save('config', path, client)
            response = client.post(self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/review',
                json={'tool': 'lifeos_memory_search', 'arguments': {'query': 'authenticated PULSE'}})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['status'], 'ok', response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mode & 0o777), before)

    def test_later_edit_after_interruption_survives_recovery(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            self.interrupt_save('principal-identity', path, client)
            path.write_text('# Synthetic later edit after interrupted save\n')
            later = path.read_bytes()
            response = self.read(client)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(path.read_bytes(), later)

    def test_owner_revocation_after_real_snapshot_refuses_publication(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client)
            request = {'identifier': 'principal-identity', 'content': '# Synthetic revoked core save\n',
                'reference': read.json()['reference'], 'request_id': 'synthetic-core-revoke'}
            before = path.read_bytes(), path.stat().st_mtime_ns
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_core_edit_process.py')),
                str(self.fixture.configuration.path), json.dumps(request), 'revoke'], capture_output=True, text=True, timeout=60,
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout), {'observed': True, 'withheld': True})
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_withheld_identity_does_not_hide_the_other_authorized_manifest_entries(self):
        path = self.seed()
        self.seed_programs()
        path.write_text('<private>Synthetic withheld manifest identity</private>\n')
        with httpx.Client(timeout=120) as client:
            self.login(client)
            response = client.get(self.native + '/api/hermes')
            self.assertEqual(response.status_code, 200, response.text)
            entries = {row['id']: row for row in response.json()['files']}
            self.assertEqual(len(entries), 24)
            self.assertFalse(entries['principal-identity']['readable'])
            self.assertFalse(entries['principal-identity']['editable'])
            self.assertIsNone(entries['principal-identity']['lines'])
            self.assertNotIn('Synthetic withheld manifest identity', response.text)
            self.assertTrue(entries['health']['readable'])

    def test_invalid_save_fields_origin_and_reused_request_ids_preserve_the_file(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client)
            valid = {'content': '# Synthetic saved core source\n', 'reference': read.json()['reference'],
                'request_id': 'synthetic-core-request-binding'}
            before = path.read_bytes()
            for changes in ({'reference': ''}, {'request_id': ''}, {'content': 1}, {'extra': True}):
                with self.subTest(changes=changes):
                    response = client.put(self.native + '/api/hermes/file/principal-identity', json={**valid, **changes})
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(path.read_bytes(), before)
            response = client.put(self.native + '/api/hermes/file/principal-identity', json=valid,
                headers={'Origin': 'https://synthetic-foreign.example.invalid'})
            self.assertEqual(response.status_code, 403, response.text)
            self.assertEqual(path.read_bytes(), before)
            response = client.put(self.native + '/api/hermes/file/principal-identity', json=valid)
            self.assertEqual(response.status_code, 200, response.text)
            saved = path.read_bytes()
            response = client.put(self.native + '/api/hermes/file/principal-identity', json={**valid, 'content': '# Another request body'})
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(path.read_bytes(), saved)


    def test_active_installation_or_turn_lock_refuses_core_save(self):
        from lifeos_hook_bridge.installation_lock import installation_lock
        from lifeos_hook_bridge import program_lock
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            reference = self.read(client).json()['reference']
            body = {'content': '# Must wait for program authority\n', 'reference': reference,
                'request_id': 'synthetic-core-lock-refusal'}
            for lock in (installation_lock(self.fixture.configuration.path.parent),
                         program_lock.exclusive(self.fixture.configuration.path.parent, 0)):
                with self.subTest(lock=type(lock).__name__), lock:
                    before = path.read_bytes()
                    response = client.put(self.native + '/api/hermes/file/principal-identity', json=body)
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertEqual(path.read_bytes(), before)

    def test_program_swap_refuses_core_reads_before_disclosure(self):
        from lifeos_hook_bridge import program_lock
        self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            with program_lock.exclusive(self.fixture.configuration.path.parent, 0):
                response = self.read(client)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertNotIn('SyntheticCoreEditorIdentity', response.text)

    def test_pending_core_recovery_waits_for_program_installation(self):
        from lifeos_hook_bridge.installation_lock import installation_lock
        path = self.seed()
        before = path.read_bytes()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            self.interrupt_save('principal-identity', path, client)
            interrupted = path.read_bytes()
            with installation_lock(self.fixture.configuration.path.parent):
                response = self.read(client)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(path.read_bytes(), interrupted)
            self.assertEqual(self.read(client).status_code, 200)
            self.assertEqual(path.read_bytes(), before)

    def test_native_core_save_preserves_the_declared_large_content_limit(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            body = {'content': '# Synthetic bounded core file\n' + ('Public synthetic line\n' * 8000),
                'reference': self.read(client).json()['reference'], 'request_id': 'synthetic-large-core-edit'}
            response = client.put(self.native + '/api/hermes/file/principal-identity', json=body)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(path.read_text(), body['content'])

    def test_invalid_configuration_withholds_only_its_own_row(self):
        self.seed()
        self.seed_programs()
        path = self.fixture.configuration.path.parent / 'config.yaml'
        path.write_text('model: [incomplete\n')
        with httpx.Client(timeout=60) as client:
            self.login(client)
            response = client.get(self.native + '/api/hermes')
            self.assertEqual(response.status_code, 200, response.text)
            rows = {row['id']: row for row in response.json()['files']}
            self.assertFalse(rows['config']['readable'])
            self.assertFalse(rows['config']['editable'])
            self.assertTrue(rows['principal-identity']['readable'])
            self.assertEqual(self.read(client, 'config').status_code, 503)

    def test_invalid_bearer_cannot_borrow_an_owner_cookie(self):
        path = self.seed()
        with httpx.Client(timeout=60) as client:
            self.login(client)
            read = self.read(client)
            before = path.read_bytes()
            response = self.read(client)
            self.assertEqual(response.status_code, 200, response.text)
            response = client.get(self.native + '/api/hermes/file/principal-identity',
                headers={'Authorization': 'Bearer synthetic-invalid'})
            self.assertEqual(response.status_code, 401, response.text)
            self.assertNotIn('SyntheticCoreEditorIdentity', response.text)
            response = client.put(self.native + '/api/hermes/file/principal-identity',
                json={'content': '# Synthetic bearer bypass', 'reference': read.json()['reference'], 'request_id': 'synthetic-denied-bearer'},
                headers={'Authorization': 'Bearer synthetic-invalid'})
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(path.read_bytes(), before)

    def test_remount_requires_current_owner_and_empty_fixed_arguments(self):
        response = httpx.post(self.native + '/api/hermes/remount')
        self.assertEqual(response.status_code, 401, response.text)
        with httpx.Client(timeout=60) as client:
            self.login(client)
            for suffix, body in (('?profile=other', b''), ('', b'{}')):
                response = client.post(self.native + '/api/hermes/remount' + suffix, content=body)
                self.assertEqual(response.status_code, 400, response.text)
            self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = client.post(self.native + '/api/hermes/remount')
            self.assertEqual(response.status_code, 403, response.text)


if __name__ == '__main__':
    unittest.main()
