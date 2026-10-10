# ABOUTME: Checks actual native Doctor diagnostics under current owner admission.
# ABOUTME: Preserves manifest and hook reconciliation while excluding raw private sources and caches.
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
from test_memory_native import OWNER
from test_memory_registered_modules import MemoryRegisteredModuleCases
from test_memory_personal_modules import MemoryPersonalModuleCases


class MemoryDoctorTests(MemoryRegisteredModuleCases, unittest.TestCase):
    start_module = MemoryPersonalModuleCases.start_module
    native_module = 'doctor.ts'
    route = '/api/doctor'
    source_relative = 'LIFEOS/MEMORY/STATE/capabilities.json'
    source_body = {'updatedAt': '2026-10-09T00:00:00Z', 'capabilities': {
        'synthetic-doctor': {'state': 'live', 'checkedAt': '2026-10-09T00:00:00Z',
            'ttlHours': 24, 'detail': 'MARKER', 'fixCmd': None, 'probeClass': 'offline'}}}
    additional_sources = {
        'LIFEOS/MEMORY/STATE/doctor-heartbeat.json': '{"ranAt":"2026-10-09T00:00:00Z","network":false}',
        'settings.json': '{"hooks":{"PreToolUse":[{"hooks":[{"command":"bun SyntheticDispatch.hook.ts"}]}]}}',
        'hooks/SyntheticDispatch.hook.ts': 'import {synthetic} from "./SyntheticIndirect.hook";\n',
        'hooks/SyntheticIndirect.hook.ts': 'export const synthetic = true;\n',
        'hooks/SyntheticUnwired.hook.sh': '#!/bin/sh\nexit 0\n',
    }

    def seed(self, marker='SyntheticRegisteredCurrent'):
        path = MemoryRegisteredModuleCases.seed(self, marker)
        hooks = self.root / 'hooks'
        if hooks.is_symlink(): hooks.unlink()
        hooks.mkdir(exist_ok=True)
        for relative, content in self.additional_sources.items():
            if relative.endswith('/doctor-heartbeat.json'):
                content = json.dumps({'ranAt': datetime.now(timezone.utc).isoformat(), 'network': False})
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        return path

    @staticmethod
    def stable(body):
        if isinstance(body.get('heartbeat'), dict): body['heartbeat'].pop('ageMs', None)
        return body

    def original(self):
        return self.stable(MemoryRegisteredModuleCases.original(self))

    def test_original_native_sources_absence_and_malformed_json_characterization(self):
        path = self.seed()
        body = self.original()
        self.assertEqual(body['manifest']['capabilities'][0]['detail'], 'SyntheticRegisteredCurrent')
        self.assertEqual(body['reconcile']['unwired'], ['SyntheticUnwired.hook.sh'])
        self.assertEqual(body['reconcile']['missing'], [])
        self.assertTrue(body['heartbeat']['present'])
        self.assertEqual(MemoryPersonalModuleCases.original(self, self.route + '/health'),
            {'status': 'stopped', 'details': {'heartbeat': 'fresh'}})
        self.assertEqual(MemoryPersonalModuleCases.original(self, self.route + '/health', running=True),
            {'status': 'healthy', 'details': {'heartbeat': 'fresh'}})
        path.unlink()
        self.assertFalse(self.original()['manifest']['present'])
        path.write_text('{"capabilities":')
        self.assertFalse(self.original()['manifest']['present'])

    def test_admitted_fields_and_absence_preserve_actual_native_response(self):
        path = self.seed()
        before = [(self.root / relative).read_bytes() for relative in (self.source_relative, *self.additional_sources)]
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for absent in (False, True):
                if absent:
                    self.assertEqual([(self.root / relative).read_bytes() for relative in
                        (self.source_relative, *self.additional_sources)], before)
                    path.unlink()
                for suffix in ('', '/', '/state'):
                    response = client.get(self.native + self.route + suffix)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(self.stable(response.json()), self.original())
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_status_health_and_started_runtime_preserve_native_heartbeat_fields(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for running in (False, True):
                if running: self.start_module()
                for suffix in ('/status', '/health'):
                    response = client.get(self.native + self.route + suffix)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), MemoryPersonalModuleCases.original(self, self.route + suffix,
                        running=running))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
        response = httpx.get(self.native + self.route + '/health')
        self.assertEqual(response.status_code, 401, response.text[:300])

    def test_current_hook_selection_and_missing_registration_preserve_native_reconciliation(self):
        self.seed()
        settings = self.root / 'settings.json'
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            settings.write_text('{"hooks":{"PreToolUse":[{"command":"bun SyntheticMissing.hook.ts"}]}}')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(self.stable(response.json()), self.original())
            self.assertEqual(response.json()['reconcile']['missing'], ['SyntheticMissing.hook.ts'])

    def test_private_hook_content_cannot_return_or_reuse_reconcile_cache(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            path = self.root / 'hooks/SyntheticDispatch.hook.ts'
            path.write_text('// <private>SyntheticDoctorHidden</private>\n')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticDoctorHidden', response.text)
            response = client.get(self.native + self.route + '/health')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), {'status': 'stopped', 'details': {'heartbeat': 'fresh'}})

    def test_hook_directory_selection_changes_after_actual_render_withhold_delivery(self):
        self.seed()
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_registered_process.py')),
            str(self.fixture.configuration.path), 'doctor', 'hooks/SyntheticDispatch.hook.ts', 'selection'],
            capture_output=True, text=True, timeout=30,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_hook_discovery_refuses_redirects_and_excessive_entries(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            path = self.root / 'hooks/SyntheticDispatch.hook.ts'
            external = self.fixture.home / 'synthetic-doctor-outside'
            external.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(external)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            path.unlink()
            path.write_bytes(external.read_bytes())
            for index in range(2049): (self.root / 'hooks' / ('synthetic-entry-' + str(index))).touch()
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])

    def test_exact_review_restores_only_current_safe_old_source(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated Doctor retirement',
            title='', project='', request_id='doctor-review-save')
        memory.forget(OWNER, saved['reference'], 'doctor-review-forget')
        relatives = [self.source_relative, *self.additional_sources]
        for relative in relatives: os.utime(self.root / relative, (1, 1))
        before = [((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns) for relative in relatives]
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 503)
            selected = preview(memory, OWNER, relatives)
            self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
            self.assertEqual(approve(memory, OWNER, relatives, selected['signature'])['status'], 'committed')
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
        self.assertEqual([((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns)
            for relative in relatives], before)


if __name__ == '__main__': unittest.main()
