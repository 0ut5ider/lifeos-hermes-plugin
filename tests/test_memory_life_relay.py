# ABOUTME: Compares native Life home and goals views through authenticated owner HTTP sessions.
# ABOUTME: Checks restricted sources, retirement, revocation, and fixed routes without raw fallback.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


class MemoryLifeRelayTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def seed(self):
        directory = self.root / 'LIFEOS/USER/TELOS'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'GOALS.md').write_text('- G1: SyntheticLifeCurrentGoal\n')
        (directory / 'CURRENT.md').write_text('### Synthetic domain\nSynthetic current domain\n\n## Next likely actions\n1. Synthetic next step\n')
        (directory / 'SPARKS.md').write_text('### Synthetic only spark\n')
        return directory

    def original(self, route):
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = 'import {startObservability,handleObservabilityRequest} from ' + json.dumps(str(
            source / 'LIFEOS/PULSE/Observability/observability.ts')) + ';startObservability({enabled:true});' + \
            'const response=await handleObservabilityRequest(new Request("http://127.0.0.1"+' + json.dumps(route) + '));' + \
            'if(!response)throw new Error("Missing native Life response");console.log(await response.text());'
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=40,
            env=dict(os.environ, HOME=str(self.fixture.home), LIFEOS_DIR=str(self.root / 'LIFEOS')))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_admitted_home_goals_and_card_preserve_native_fields(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for route in ('/api/life/home', '/api/life/goals', '/api/observability/life-card'):
                with self.subTest(route=route):
                    result = client.get(self.native + route)
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertEqual(result.json(), self.original(route))

    def test_anonymous_and_ambient_owner_cannot_read_goals(self):
        self.seed()
        for route in ('/api/life/home', '/api/life/goals', '/api/observability/life-card'):
            with self.subTest(route=route):
                result = httpx.get(self.native + route, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(result.status_code, 401, result.text)
                self.assertNotIn('SyntheticLifeCurrentGoal', result.text)
                self.assertEqual(result.headers.get('cache-control'), 'no-store')

    def test_revoked_dashboard_binding_refuses_personal_goals(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            result = client.get(self.native + '/api/life/goals')
            self.assertEqual(result.status_code, 403, result.text)
            self.assertNotIn('SyntheticLifeCurrentGoal', result.text)

    def test_private_goals_do_not_enter_home_or_master_text(self):
        directory = self.seed()
        (directory / 'GOALS.md').write_text('- G1: <private>SyntheticLifePrivateGoal</private>\n')
        (directory / 'TELOS.md').write_text('## Goals\n- G2: <private>SyntheticLifePrivateMaster</private>\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for route in ('/api/life/home', '/api/life/goals'):
                result = client.get(self.native + route)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertNotIn('SyntheticLifePrivate', result.text)

    def test_forgotten_goal_is_removed_from_views_and_retained_in_original_file(self):
        directory = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticLifeCurrentGoal',
            title='', project='', request_id='synthetic-life-retained')
        memory.forget(OWNER, saved['reference'], 'synthetic-life-forget')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for route in ('/api/life/home', '/api/life/goals'):
                result = client.get(self.native + route)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertNotIn('SyntheticLifeCurrentGoal', result.text)
        self.assertIn('SyntheticLifeCurrentGoal', (directory / 'GOALS.md').read_text())

    def test_corrected_goal_cannot_return_from_the_retained_source(self):
        directory = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticLifeCurrentGoal',
            title='', project='', request_id='synthetic-life-correction-source')
        result = memory.correct(OWNER, saved['reference'], 'RULE: SyntheticLifeReplacementGoal',
            'synthetic-life-correction')
        self.assertEqual(result['status'], 'committed', result)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = client.get(self.native + '/api/life/goals')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticLifeCurrentGoal', response.text)
        self.assertIn('SyntheticLifeCurrentGoal', (directory / 'GOALS.md').read_text())
        self.assertTrue(memory.recall(OWNER, 'SyntheticLifeReplacementGoal'))

    def test_connector_loss_preserves_managed_refusal(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            result = client.get(self.native + '/api/life/home')
            self.assertEqual(result.status_code, 503, result.text)
            self.assertNotIn('SyntheticLifeCurrentGoal', result.text)

    def test_cross_origin_invalid_bearer_query_and_method_refuse(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for method, route, headers, expected in (
                ('GET', '/api/life/home', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '/api/life/home', {'Authorization': 'Bearer synthetic-invalid'}, 401),
                ('GET', '/api/life/goals?owner=other', {}, 400),
                ('POST', '/api/life/goals', {}, 405),
            ):
                with self.subTest(method=method, route=route):
                    result = client.request(method, self.native + route, headers=headers)
                    self.assertEqual(result.status_code, expected, result.text)
                    self.assertNotIn('SyntheticLifeCurrentGoal', result.text)

    def test_unified_sections_and_legacy_fallback_preserve_native_precedence(self):
        directory = self.seed()
        (directory / 'TELOS.md').write_text('## Goals\n- G2: Synthetic unified goal\n## Mission\n### M1: Synthetic mission\nSynthetic mission body\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            result = client.get(self.native + '/api/life/goals')
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json(), self.original('/api/life/goals'))
            self.assertNotIn('SyntheticLifeCurrentGoal', json.dumps(result.json()['goals']))

    def test_empty_views_preserve_native_response_fields(self):
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for route in ('/api/life/home', '/api/life/goals'):
                result = client.get(self.native + route)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json(), self.original(route))

    def test_source_or_authority_change_after_actual_render_withholds_output(self):
        for mode in ('source', 'authority'):
            with self.subTest(mode=mode):
                self.seed()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_life_process.py')),
                    str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_redirected_goals_refuse_without_reading_the_external_source(self):
        directory = self.seed()
        outside = self.fixture.home / 'synthetic-outside-goals.md'
        outside.write_text('- G1: SyntheticLifeOutsideGoal\n')
        path = directory / 'GOALS.md'
        path.unlink()
        path.symlink_to(outside)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            result = client.get(self.native + '/api/life/home')
            self.assertEqual(result.status_code, 503, result.text)
            self.assertNotIn('SyntheticLifeOutsideGoal', result.text)

    def test_oversize_goals_refuse_without_returning_the_source(self):
        directory = self.seed()
        (directory / 'GOALS.md').write_text('SyntheticLifeOversizeGoal' * 12000)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            result = client.get(self.native + '/api/life/goals')
            self.assertEqual(result.status_code, 503, result.text)
            self.assertNotIn('SyntheticLifeOversizeGoal', result.text)

    def test_hardlinked_goals_refuse_before_native_rendering(self):
        directory = self.seed()
        os.link(directory / 'GOALS.md', self.fixture.home / 'synthetic-goals-link.md')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            result = client.get(self.native + '/api/life/home')
            self.assertEqual(result.status_code, 503, result.text)
            self.assertNotIn('SyntheticLifeCurrentGoal', result.text)


if __name__ == '__main__':
    unittest.main()
