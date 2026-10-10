# ABOUTME: Checks onboarding identity and personalization through actual authenticated native HTTP.
# ABOUTME: Preserves template behavior while excluding private, retired, and redirected source text.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_operational_views as operational_fixture
from test_memory_native import OWNER


class MemoryOnboardingTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = operational_fixture.MemoryOperationalViewsTests.setUp
    create_fixture = operational_fixture.MemoryOperationalViewsTests.create_fixture
    native_module_name = operational_fixture.MemoryOperationalViewsTests.native_module_name
    stop_dashboard = operational_fixture.MemoryOperationalViewsTests.stop_dashboard
    stop_pulse = operational_fixture.MemoryOperationalViewsTests.stop_pulse
    login = operational_fixture.MemoryOperationalViewsTests.login
    original = operational_fixture.MemoryOperationalViewsTests.original

    def seed(self, name='SyntheticOnboardingAssistant', mission=''):
        parent = self.root / 'LIFEOS/USER'
        identity = parent / 'DIGITAL_ASSISTANT/DA_IDENTITY.md'
        identity.parent.mkdir(parents=True, exist_ok=True)
        identity.write_text('# Assistant\n\n**Name:** ' + name + '\n')
        telos = parent / 'TELOS/TELOS.md'
        telos.parent.mkdir(parents=True, exist_ok=True)
        telos.write_text('# TELOS\n\n## Mission\n' + mission + '\n')
        for filename in ('MISSION.md', 'GOALS.md', 'PROBLEMS.md', 'STRATEGIES.md', 'CHALLENGES.md'):
            (telos.parent / filename).write_text('# ' + filename.removesuffix('.md') + '\n')
        marker = parent / '.template-mode'
        marker.write_text('')
        return identity, telos, marker

    def test_anonymous_and_ambient_flags_cannot_read_assistant_name(self):
        self.seed()
        response = httpx.get(self.native + '/api/onboarding/state', headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 401, response.text[:300])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticOnboardingAssistant', response.text)

    def test_native_name_and_template_personalization_fields_match(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for name, mission, marker in (
                    ('SyntheticOnboardingAssistant', '', True),
                    ('SyntheticOnboardingAssistant', '### M0: (sample) Synthetic example\n', True),
                    ('SyntheticOnboardingAssistant', '### M0: Synthetic real mission\n', True),
                    ('your DA', '', True), ('SyntheticOnboardingAssistant', '', False)):
                with self.subTest(name=name, mission=mission, marker=marker):
                    identity, telos, flag = self.seed(name, mission)
                    if not marker: flag.unlink()
                    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in (identity, telos)]
                    response = client.get(self.native + '/api/onboarding/state')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), self.original('/api/onboarding/state'))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in (identity, telos)], before)

    def test_private_name_and_mission_cannot_change_public_onboarding(self):
        self.seed('<private>SyntheticOnboardingPrivate</private>',
                  '### M0: <private>SyntheticOnboardingPrivate</private>\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/onboarding/state')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), {'templateMode': True, 'daName': 'your DA', 'interviewCommand': '/interview'})
            self.assertNotIn('SyntheticOnboardingPrivate', response.text)

    def test_forgotten_assistant_name_cannot_return_from_original_identity(self):
        self.seed('SyntheticOnboardingRetired')
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticOnboardingRetired',
            title='', project='', request_id='onboarding-retained')
        memory.forget(OWNER, saved['reference'], 'onboarding-forget')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/onboarding/state')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['daName'], 'your DA')
            self.assertNotIn('SyntheticOnboardingRetired', response.text)

    def test_revocation_connector_loss_and_redirected_identity_refuse(self):
        identity, _, _ = self.seed()
        outside = self.fixture.home / 'synthetic-onboarding-outside.md'
        outside.write_bytes(identity.read_bytes())
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'revoked', 'missing'):
                with self.subTest(mode=mode):
                    if mode in ('symlink', 'hardlink'):
                        identity.unlink()
                        if mode == 'symlink': identity.symlink_to(outside)
                        else: os.link(outside, identity)
                        expected = 503
                    elif mode == 'revoked':
                        identity.unlink()
                        self.seed()
                        self.fixture.configuration.update(lambda value: value['accounts'].clear())
                        expected = 403
                    else:
                        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
                        expected = 503
                    response = client.get(self.native + '/api/onboarding/state')
                    self.assertEqual(response.status_code, expected, response.text[:300])
                    self.assertNotIn('SyntheticOnboardingAssistant', response.text)

    def test_methods_selectors_origin_and_invalid_bearer_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, target, headers, status in (
                    ('POST', '/api/onboarding/state', {}, 405), ('GET', '/api/onboarding/state?owner=other', {}, 400),
                    ('GET', '/api/onboarding/state', {'Origin': 'https://outside.invalid'}, 403),
                    ('GET', '/api/onboarding/state', {'Authorization': 'Bearer synthetic-invalid'}, 401)):
                with self.subTest(method=method, target=target):
                    response = client.request(method, self.native + target, headers=headers)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertNotIn('SyntheticOnboardingAssistant', response.text)

    def test_each_native_legacy_personalization_fallback_matches(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for filename, prefix in (('MISSION', 'M'), ('GOALS', 'G'), ('PROBLEMS', 'P'),
                                     ('STRATEGIES', 'S'), ('CHALLENGES', 'C')):
                with self.subTest(filename=filename):
                    _, telos, _ = self.seed()
                    fallback = telos.parent / (filename + '.md')
                    fallback.write_text('# ' + filename + '\n### ' + prefix + '0: Synthetic real entry\n')
                    response = client.get(self.native + '/api/onboarding/state')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), self.original('/api/onboarding/state'))
                    self.assertFalse(response.json()['templateMode'])
                    fallback.write_text('# ' + filename + '\n### ' + prefix +
                                        '0: <private>SyntheticHiddenEntry</private>\n')
                    response = client.get(self.native + '/api/onboarding/state')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertTrue(response.json()['templateMode'])

    def test_marker_redirection_source_size_and_invalid_utf8_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('marker-link', 'marker-hardlink', 'oversize', 'utf8'):
                with self.subTest(mode=mode):
                    marker = self.root / 'LIFEOS/USER/.template-mode'
                    if marker.exists() or marker.is_symlink(): marker.unlink()
                    identity, _, marker = self.seed()
                    if mode.startswith('marker-'):
                        outside = self.fixture.home / 'synthetic-marker-outside'
                        outside.write_text('')
                        marker.unlink()
                        if mode == 'marker-link': marker.symlink_to(outside)
                        else: os.link(outside, marker)
                    elif mode == 'oversize': identity.write_text('x' * (256 * 1024 + 1))
                    else: identity.write_bytes(b'**Name:** SyntheticOnboardingAssistant\xff')
                    response = client.get(self.native + '/api/onboarding/state')
                    self.assertEqual(response.status_code, 503, response.text[:300])
                    self.assertNotIn('SyntheticOnboardingAssistant', response.text)

    def test_actual_render_rechecks_source_and_marker_before_delivery(self):
        for mode in ('source', 'created', 'metadata', 'marker-created', 'marker-removed', 'authority'):
            with self.subTest(mode=mode):
                identity, _, marker = self.seed()
                if mode == 'created': identity.unlink()
                if mode == 'marker-created': marker.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name(
                    'memory_onboarding_process.py')), str(self.fixture.configuration.path), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_exact_review_restores_safe_old_identity_and_mission_without_writes(self):
        identity, telos, _ = self.seed('SyntheticOnboardingAssistant', '### M0: Synthetic real mission\n')
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedOnboardingRetirement',
            title='', project='', request_id='onboarding-review-retained')
        memory.forget(OWNER, saved['reference'], 'onboarding-review-forget')
        for path in (identity, telos): os.utime(path, (1_577_836_800, 1_577_836_800))
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in (identity, telos)]
        endpoint = self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/sources'
        paths = ['LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md', 'LIFEOS/USER/TELOS/TELOS.md']
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/onboarding/state')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['daName'], 'your DA')
            preview = client.post(endpoint + '/preview', json={'paths': paths})
            self.assertEqual(preview.status_code, 200, preview.text[:300])
            self.assertTrue(all(source['accepted'] for source in preview.json()['sources']))
            approval = client.post(endpoint, json={'paths': paths, 'signature': preview.json()['signature']})
            self.assertEqual(approval.status_code, 200, approval.text[:300])
            self.assertEqual(approval.json()['status'], 'committed')
            response = client.get(self.native + '/api/onboarding/state')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), self.original('/api/onboarding/state'))
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in (identity, telos)], before)
