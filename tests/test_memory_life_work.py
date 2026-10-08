# ABOUTME: Compares local native work views through actual authenticated owner HTTP sessions.
# ABOUTME: Checks project and session source admission without enabling the optional GitHub work integration.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryLifeWorkTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login
    original = life_fixture.MemoryLifeRelayTests.original

    def seed(self):
        directory = self.root / 'LIFEOS/USER'
        (directory / 'PROJECTS.md').write_text('| Project | Path | URL |\n|---|---|---|\n'
            '| **SyntheticWorkProject** | /synthetic/local/project | https://synthetic.invalid |\n')
        (directory / 'TELOS').mkdir(exist_ok=True)
        (directory / 'TELOS/CURRENT.md').write_text('**focus:** SyntheticWorkFocus\n'
            '**current_project:** SyntheticWorkProject\n**active_workstreams:** SyntheticWorkStream\n')
        state = self.root / 'LIFEOS/MEMORY/STATE'
        state.mkdir(parents=True, exist_ok=True)
        (state / 'work.json').write_text(json.dumps({'sessions': {
            'synthetic-active': {'task': 'SyntheticWorkSession', 'phase': 'implement', 'progress': '1/3', 'effort': 'standard'},
            'synthetic-complete': {'task': 'SyntheticCompletedSession', 'phase': 'complete'},
            'synthetic-idle': {'task': 'SyntheticIdleSession', 'phase': 'idle'},
        }}))
        return directory

    def get(self, client): return client.get(self.native + '/api/life/work')

    def test_table_projects_and_active_sessions_match_native(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/work'))
            self.assertEqual(response.json()['algorithmSessions'][0]['task'], 'SyntheticWorkSession')
            self.assertEqual(len(response.json()['algorithmSessions']), 1)
            self.assertEqual(response.json()['currentFocus'], 'SyntheticWorkFocus')

    def test_narrative_projects_and_unified_current_precedence_match_native(self):
        directory = self.seed()
        (directory / 'PROJECTS.md').write_text('## Synthetic narrative project\nSynthetic project details\n')
        (directory / 'TELOS/TELOS.md').write_text('## Current State\n**focus:** Synthetic unified focus\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/work'))
            self.assertEqual(response.json()['currentFocus'], 'Synthetic unified focus')

    def test_empty_work_view_matches_native(self):
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/work'))

    def test_anonymous_revoked_and_missing_connector_refuse_work(self):
        self.seed()
        response = httpx.get(self.native + '/api/life/work')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertNotIn('SyntheticWork', response.text)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
            original_connector = connector.read_bytes()
            connector.unlink()
            self.assertEqual(self.get(client).status_code, 503)
            connector.write_bytes(original_connector)
            connector.chmod(0o600)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(self.get(client).status_code, 403)

    def test_private_projects_current_focus_and_decoded_sessions_do_not_publish(self):
        directory = self.seed()
        (directory / 'PROJECTS.md').write_text('## <private>SyntheticPrivateProject</private>\n')
        (directory / 'TELOS/CURRENT.md').write_text('**focus:** <private>SyntheticPrivateFocus</private>\n')
        (self.root / 'LIFEOS/MEMORY/STATE/work.json').write_text(
            '{"sessions":{"synthetic":{"task":"\\u003cprivate\\u003eSyntheticPrivateSession\\u003c/private\\u003e","phase":"implement"}}}')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivate', response.text)

    def test_current_escaped_retired_session_cannot_return(self):
        directory = self.seed()
        path = self.root / 'LIFEOS/MEMORY/STATE/work.json'
        path.write_text('{"sessions":{"synthetic":{"task":"Synthetic\\u0052etiredSession","phase":"implement"}}}')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertIn('SyntheticRetiredSession', self.get(client).text)
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: SyntheticRetiredSession',
            title='', project='', request_id='synthetic-retired-work-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-retired-work-forget')
        for source in (path, directory / 'PROJECTS.md', directory / 'TELOS/CURRENT.md'):
            os.utime(source, None)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticRetiredSession', response.text)
            self.assertIn('SyntheticWorkProject', response.text)
        self.assertIn('\\u0052etiredSession', path.read_text())

    def test_oversize_or_redirected_project_source_refuses(self):
        directory = self.seed()
        path = directory / 'PROJECTS.md'
        path.write_text('SyntheticOversizeWork' * 15000)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)
            external = self.fixture.home / 'synthetic-external-project.md'
            path.rename(external)
            path.symlink_to(external)
            self.assertEqual(self.get(client).status_code, 503)

    def test_source_or_account_change_after_render_withholds_response(self):
        self.seed()
        for mode in ('source', 'session', 'created', 'authority'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_life_process.py')),
                    str(self.fixture.configuration.path), mode, '/api/life/work'], capture_output=True, text=True,
                    timeout=40, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_project_and_session_display_limits_match_native(self):
        directory = self.seed()
        (directory / 'PROJECTS.md').write_text('\n'.join('## SyntheticProject' + str(number) for number in range(30)))
        (self.root / 'LIFEOS/MEMORY/STATE/work.json').write_text(json.dumps({'sessions': {
            'synthetic-' + str(number): {'task': 'SyntheticTask' + str(number), 'phase': 'implement'}
            for number in range(30)}}))
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/work'))
            self.assertEqual(len(response.json()['projects']), 20)
            self.assertEqual(len(response.json()['algorithmSessions']), 10)

    def test_malformed_session_json_preserves_native_empty_session_default(self):
        self.seed()
        (self.root / 'LIFEOS/MEMORY/STATE/work.json').write_text('synthetic malformed JSON')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/work'))
            self.assertEqual(response.json()['algorithmSessions'], [])

    def test_hardlinked_session_source_refuses(self):
        self.seed()
        os.link(self.root / 'LIFEOS/MEMORY/STATE/work.json', self.fixture.home / 'synthetic-session-alias.json')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)

    def test_cross_origin_bearer_selectors_and_writes_refuse(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for method, suffix, headers, status in (
                ('GET', '', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '', {'Authorization': 'Bearer synthetic-invalid'}, 401),
                ('GET', '?owner=another', {}, 400),
                ('POST', '', {}, 405),
            ):
                with self.subTest(method=method, suffix=suffix, headers=headers):
                    response = client.request(method, self.native + '/api/life/work' + suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn('SyntheticWork', response.text)


if __name__ == '__main__':
    unittest.main()
