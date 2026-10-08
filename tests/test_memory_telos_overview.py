# ABOUTME: Verifies the native TELOS overview through real authenticated owner services.
# ABOUTME: Compares native fields and tests current sources without optional remote integrations.
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


class MemoryTelosOverviewTests(unittest.TestCase):
    native_module = 'observability.ts'
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def setUp(self):
        self.guard = socket.socket()
        self.guard.bind(('127.0.0.1', 0))
        self.addCleanup(self.guard.close)
        self.pulse = f'http://127.0.0.1:{self.guard.getsockname()[1]}'
        previous = os.environ.get('PULSE_URL')
        os.environ['PULSE_URL'] = self.pulse
        def restore():
            if previous is None: os.environ.pop('PULSE_URL', None)
            else: os.environ['PULSE_URL'] = previous
        self.addCleanup(restore)
        relay_fixture.MemoryPulseRelayTests.setUp(self)
        self.route = '/api/telos/overview'

    def seed(self):
        directory = self.root / 'LIFEOS/USER/TELOS'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'TELOS.md').write_text('## Mission\n### M1: Synthetic mission\n'
            '- Summary: Synthetic mission summary\n- References: P1\n'
            '## Goals\n### G1: SyntheticLifeCurrentGoal\n- KPI: Synthetic measure\n'
            '- Target: Synthetic target\n- References: P1\n'
            '## Problems\n### P1: Synthetic problem\n- References: M1\n'
            '## Strategies\n### S1: Synthetic strategy\n- References: C1, G1\n'
            '## Challenges\n### C1: Synthetic challenge\n- References: G1\n'
            '## Current State\n**Focus:** Synthetic current focus\n**Mood:** Steady\n'
            '## Ideal State\n### Health\nSynthetic ideal health\n')
        (directory / 'BOOKS.md').write_text('- Synthetic book\n')
        (directory / 'MOVIES.md').write_text('- Synthetic film\n')
        (directory / 'AUTHORS.md').write_text('- Synthetic author\n')
        for name in ('CURRENT_STATE', 'IDEAL_STATE'): (directory / name).mkdir(exist_ok=True)
        (directory / 'CURRENT_STATE/SNAPSHOT.md').write_text('**Mood:** 8/10\n**Energy:** 7/10\n**Focus:** 6/10\n')
        (directory / 'IDEAL_STATE/HEALTH.md').write_text('# Health\nSynthetic health target\n')
        (directory / 'CURRENT_STATE/HEALTH.md').write_text('# Health\n**Score:** 7/10\n')
        for relative, content in (
            ('PRINCIPAL/PRINCIPAL_IDENTITY.md', '**Name:** Synthetic Principal\n'),
            ('DIGITAL_ASSISTANT/DA_IDENTITY.md', '**Name:** Synthetic Assistant\n'),
            ('PROJECTS.md', '**Fleet: Synthetic Worker / Synthetic Helper**\n')):
            path = self.root / 'LIFEOS/USER' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return directory

    def memory(self):
        return self.fixture.fixture.fixture.fixture.fixture.memory

    def original(self):
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {startObservability,handleObservabilityRequest} from ' + json.dumps(str(
            source / 'LIFEOS/PULSE/Observability/observability.ts')) + ';\n'
            'startObservability({enabled:true});\n'
            'const response=await handleObservabilityRequest(new Request("http://127.0.0.1/api/telos/overview"));\n'
            'if(!response)throw new Error("Missing native overview");console.log(await response.text());\n')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=30, env=dict(os.environ, HOME=str(self.fixture.home), PULSE_URL=self.pulse,
                                 LIFEOS_DIR=str(self.root / 'LIFEOS')))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_anonymous_and_ambient_owner_refuse_before_reading_personal_sources(self):
        self.seed()
        response = httpx.get(self.native + self.route, headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticLifeCurrentGoal', response.text)

    def test_empty_overview_preserves_native_fields(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original())

    def test_admitted_overview_preserves_native_parsing_and_identity(self):
        directory = self.seed()
        state = self.memory()._native('lifeos_state', sources={
            'IDEAL_STATE/HEALTH.md': (directory / 'IDEAL_STATE/HEALTH.md').read_text(),
            'CURRENT_STATE/HEALTH.md': (directory / 'CURRENT_STATE/HEALTH.md').read_text()}, json_output=True)
        (directory / 'LIFEOS_STATE.json').write_text(state['content'])
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original())
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(response.json()['snapshot'], [
                {'id': 'mood', 'label': 'Mood', 'v': 8, 'of': 10},
                {'id': 'energy', 'label': 'Energy', 'v': 7, 'of': 10},
                {'id': 'focus', 'label': 'Focus', 'v': 6, 'of': 10}])

    def test_stale_state_cache_cannot_override_current_dimension_sources(self):
        directory = self.seed()
        cache = directory / 'LIFEOS_STATE.json'
        cache.write_text('{"dimensions":{"health":{"pct":99}},"private":"SyntheticIgnoredCache"}')
        before = cache.read_bytes(), cache.stat().st_mtime_ns
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotEqual(response.json()['dimensions'][0]['cur'], 99)
            self.assertNotIn('SyntheticIgnoredCache', response.text)
            self.assertEqual((cache.read_bytes(), cache.stat().st_mtime_ns), before)

    def test_private_sources_do_not_enter_overview_text_snapshot_or_team(self):
        directory = self.seed()
        (directory / 'TELOS.md').write_text('## Goals\n- G1: <private>SyntheticPrivateOverview</private>\n')
        (directory / 'CURRENT_STATE/SNAPSHOT.md').write_text('**Mood:** <private>SyntheticPrivateSnapshot</private>\n')
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text(
            '**Name:** <private>SyntheticPrivatePrincipal</private>\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivate', response.text)

    def test_retired_goal_cannot_return_from_unmodified_overview_source(self):
        directory = self.seed()
        before = (directory / 'TELOS.md').read_bytes()
        saved = self.memory().remember(OWNER, category='principal', content='RULE: SyntheticLifeCurrentGoal',
            title='', project='', request_id='overview-retained')
        self.memory().forget(OWNER, saved['reference'], 'overview-forget')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticLifeCurrentGoal', response.text)
            self.assertEqual((directory / 'TELOS.md').read_bytes(), before)

    def test_legacy_goals_fallback_preserves_native_behavior(self):
        directory = self.seed()
        (directory / 'TELOS.md').unlink()
        (directory / 'GOALS.md').write_text('- G1: Synthetic legacy goal\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            original = self.original()
            self.assertEqual(body['goals'], original['goals'])
            self.assertEqual(body['meta'], original['meta'])

    def test_revoked_account_and_connector_loss_refuse_without_raw_fallback(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('SyntheticLifeCurrentGoal', response.text)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        response = httpx.get(self.native + self.route)
        self.assertEqual(response.status_code, 503, response.text)

    def test_route_selectors_method_origin_and_invalid_bearer_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, suffix, headers, status in (
                ('POST', '', {}, 405), ('GET', '?owner=other', {}, 400),
                ('GET', '', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '', {'Authorization': 'Bearer synthetic-invalid'}, 401)):
                with self.subTest(method=method, suffix=suffix, headers=headers):
                    response = client.request(method, self.native + self.route + suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn('SyntheticLifeCurrentGoal', response.text)

    def test_redirected_or_oversize_snapshot_refuses_before_disclosing_source(self):
        directory = self.seed()
        snapshot = directory / 'CURRENT_STATE/SNAPSHOT.md'
        outside = self.fixture.home / 'outside-snapshot.md'
        outside.write_text('**Mood:** SyntheticOutsideSnapshot\n')
        snapshot.unlink()
        snapshot.symlink_to(outside)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticOutsideSnapshot', response.text)
            snapshot.unlink()
            snapshot.write_text('**Mood:** SyntheticOversizeSnapshot' + 'x' * (256 * 1024))
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticOversizeSnapshot', response.text)

    def test_sources_creation_metadata_and_authority_after_actual_render_withhold_response(self):
        for mode in ('source', 'created', 'metadata', 'authority'):
            with self.subTest(mode=mode):
                directory = self.seed()
                (directory / 'IDEAL_STATE/FINANCES.md').unlink(missing_ok=True)
                result = subprocess.run([sys.executable, str(Path(__file__).with_name(
                    'memory_telos_overview_process.py')), str(self.fixture.configuration.path), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_current_dimension_change_updates_percentage_without_publishing_cache(self):
        directory = self.seed()
        current = directory / 'CURRENT_STATE/HEALTH.md'
        current.write_text('- status: have\n- status: missing\n')
        cache = directory / 'LIFEOS_STATE.json'
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['dimensions'][0]['cur'], 50)
            current.write_text('- status: have\n- status: have\n')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['dimensions'][0]['cur'], 100)
            self.assertFalse(cache.exists())

    def test_unsafe_ideal_source_cannot_create_a_dimension_presence_signal(self):
        directory = self.seed()
        (directory / 'IDEAL_STATE/HEALTH.md').write_text('<private>SyntheticPrivateIdeal</private>\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsNone(response.json()['dimensions'])

    def test_unselected_remote_work_and_bunker_sources_do_not_enter_daily_overview(self):
        self.seed()
        path = self.fixture.home / '.bunker/monitor-state.json'
        path.parent.mkdir()
        path.write_text('{"SyntheticPrivateMonitor":{"status":"green","failing":[]}}')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivateMonitor', response.text)
            for name in ('workNarrative', 'projects', 'metrics'): self.assertIsNone(response.json()[name])
