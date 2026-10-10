# ABOUTME: Exercises the native Life health response through actual authenticated HTTP sessions.
# ABOUTME: Checks content and filename admission while preserving native sections and freshness fields.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryLifeHealthTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login
    original = life_fixture.MemoryLifeRelayTests.original

    def seed(self):
        directory = self.root / 'LIFEOS/USER/HEALTH'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'CONDITIONS.md').write_text('---\nlast_updated: 2026-10-08\n---\n### Synthetic health heading\nSyntheticHealthCondition current note\n')
        (directory / 'FITNESS.md').write_text('### Synthetic fitness\nSynthetic fitness note\n')
        (directory / 'lab_results_2026-10-01.pdf').write_bytes(b'%PDF-Synthetic metadata fixture')
        return directory

    def test_admitted_health_fields_and_lab_metadata_match_native(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/health'))

    def test_anonymous_health_request_cannot_read_personal_sources(self):
        self.seed()
        response = httpx.get(self.native + '/api/life/health')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertNotIn('SyntheticHealthCondition', response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_revoked_account_cannot_read_health_sources(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('SyntheticHealthCondition', response.text)

    def test_private_markdown_does_not_publish_body_heading_or_dynamic_filename(self):
        directory = self.seed()
        (directory / 'CONDITIONS.md').write_text('<private>### Synthetic health heading\nSyntheticPrivateHealthCondition note</private>\n')
        (directory / 'SyntheticPrivateHealthFilename.md').write_text('<private>Synthetic private file</private>\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivateHealth', response.text)
            self.assertIn('Synthetic fitness note', response.text)

    def test_forgotten_health_note_cannot_return_from_the_retained_file(self):
        directory = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertIn('SyntheticHealthCondition', client.get(self.native + '/api/life/health').text)
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: SyntheticHealthCondition',
            title='', project='', request_id='synthetic-health-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-health-forget')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticHealthCondition', response.text)
        self.assertIn('SyntheticHealthCondition', (directory / 'CONDITIONS.md').read_text())

    def test_connector_loss_cannot_restore_raw_health_reads(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticHealthCondition', response.text)

    def test_redirected_health_directory_refuses_external_data(self):
        directory = self.seed()
        retained = directory.with_name('synthetic-retained-health')
        directory.rename(retained)
        directory.symlink_to(retained, target_is_directory=True)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticHealthCondition', response.text)

    def test_hardlinked_health_note_refuses(self):
        directory = self.seed()
        os.link(directory / 'CONDITIONS.md', self.fixture.home / 'synthetic-condition-link.md')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticHealthCondition', response.text)

    def test_source_directory_or_authority_change_after_render_withholds_the_response(self):
        for mode in ('source', 'entry', 'authority'):
            with self.subTest(mode=mode):
                self.seed()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_life_process.py')),
                    str(self.fixture.configuration.path), mode, '/api/life/health'], capture_output=True, text=True,
                    timeout=40, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_empty_health_view_preserves_native_fields(self):
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/health'))

    def test_leaf_filename_with_repeated_dots_preserves_native_fields(self):
        directory = self.seed()
        (directory / 'synthetic.followup..md').write_text('Synthetic admitted followup note\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/health'))

    def test_oversize_health_note_refuses_before_returning_source_text(self):
        directory = self.seed()
        (directory / 'CONDITIONS.md').write_text('SyntheticHealthOversizeCondition' * 10000)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticHealthOversizeCondition', response.text)

    def test_health_discovery_has_a_fixed_count_limit(self):
        directory = self.seed()
        for number in range(2050):
            (directory / f'synthetic-{number}.md').touch()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 503, response.text)

    def test_retired_lab_filename_is_removed_from_metadata(self):
        directory = self.seed()
        filename = 'lab_results_2026-10-01.pdf'
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: ' + filename,
            title='', project='', request_id='synthetic-health-lab-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-health-lab-forget')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn(filename, response.text)
        self.assertTrue((directory / filename).is_file())


if __name__ == '__main__':
    unittest.main()
