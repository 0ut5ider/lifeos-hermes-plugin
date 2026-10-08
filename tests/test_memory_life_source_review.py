# ABOUTME: Reviews synthetic Life sources through actual authenticated owner HTTP endpoints.
# ABOUTME: Tests recovery of safe retained data and refusal of private, retired, changed, or unbound sources.
import json
import os
from pathlib import Path
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryLifeSourceReviewTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login
    original = life_fixture.MemoryLifeRelayTests.original
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/sources'

    def seed(self):
        texts = {
            'LIFEOS/USER/HEALTH/CONDITIONS.md': '## Conditions\nSyntheticReviewedCondition\n',
            'LIFEOS/USER/FINANCES/ACCOUNTS.md': '## Accounts\nSyntheticReviewedAccount\n',
            'LIFEOS/USER/FINANCES/state.json': json.dumps({'note': 'SyntheticReviewedState'}),
            'LIFEOS/USER/FINANCES/vendors.yaml': 'vendors:\n  - id: synthetic\n    name: SyntheticReviewedVendor\n    manual_monthly_usd: 10\n',
            'LIFEOS/USER/FINANCES/obligations.yaml': 'obligations:\n  - vendor: SyntheticReviewedRent\n    amount: "$120"\n    frequency: monthly\n',
            'LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml': '[principal]\nname="SyntheticOwner"\ntimezone="UTC"\ncurrency="CAD"\n'
                '[da]\nname="SyntheticAssistant"\n[da.voices.main]\nvoice_id="synthetic-voice"\n',
            'LIFEOS/MEMORY/OBSERVABILITY/vendor-costs.jsonl': json.dumps({
                'vendor': 'synthetic', 'cost_usd': 12, 'captured_at': '2026-10-08T00:00:00Z'}) + '\n',
            'LIFEOS/MEMORY/OBSERVABILITY/statement-spend.jsonl': json.dumps({'schema': 'pulse.statement_spend.v1',
                'generated_at': '2026-10-08T00:00:00Z'}) + '\n',
            'LIFEOS/USER/TELOS/CURRENT.md': '**focus:** SyntheticReviewedFocus\n',
            'LIFEOS/USER/TELOS/LEARNED.md': '## Learned\nSyntheticReviewedLesson\n',
            'LIFEOS/USER/TELOS/2036.md': '## Timeline\nSyntheticReviewedTimeline\n',
            'LIFEOS/USER/TELOS/STATUS.md': '## Status\nSyntheticReviewedStatus\n',
            'LIFEOS/USER/WORK/YOUR_COMPANIES/synthetic-company/README.md': '## Company\nSyntheticReviewedCompany\n',
            'LIFEOS/USER/WORK/YOUR_COMPANIES/synthetic-company/REVENUE/2026-10.md': '## Summary\nSyntheticReviewedRevenue\n',
        }
        for relative, text in texts.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        lab = 'LIFEOS/USER/HEALTH/lab_results_2026-10-01.pdf'
        (self.root / lab).write_bytes(b'%PDF-SyntheticOpaqueLabBody')
        return [*texts, lab, 'LIFEOS/USER/WORK/YOUR_COMPANIES/synthetic-company']

    def forget(self, claim='SyntheticReviewUnrelatedRetirement', identifier='synthetic-source-review-retirement'):
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: ' + claim,
            title='', project='', request_id=identifier)
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(memory.forget(life_fixture.OWNER, saved['reference'], identifier + '-forget')['status'], 'committed')

    def preview(self, client, paths):
        response = client.post(self.dashboard + self.endpoint + '/preview', json={'paths': paths})
        self.assertEqual(response.status_code, 200, response.text[:500])
        return response.json()

    def approve(self, client, paths, snapshot):
        response = client.post(self.dashboard + self.endpoint, json={'paths': paths, 'signature': snapshot['signature']})
        self.assertEqual(response.status_code, 200, response.text[:500])
        return response.json()

    def test_safe_old_life_sources_restore_without_changing_bytes_or_timestamps(self):
        paths = self.seed()
        files = [path for path in paths if (self.root / path).is_file()]
        before = {path: ((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns) for path in files}
        self.forget()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            self.assertNotIn('SyntheticReviewedCondition', client.get(self.native + '/api/life/health').text)
            snapshot = self.preview(client, paths)
            self.assertTrue(all(source['accepted'] for source in snapshot['sources']), snapshot)
            self.assertNotIn('SyntheticOpaqueLabBody', json.dumps(snapshot))
            self.assertEqual(self.approve(client, paths, snapshot)['status'], 'committed')
            for route in ('/api/life/health', '/api/life/finances', '/api/life/work', '/api/life/goals', '/api/life/business'):
                with self.subTest(route=route):
                    response = client.get(self.native + route)
                    self.assertEqual(response.status_code, 200, response.text[:500])
                    self.assertEqual(response.json(), self.original(route))
        for path, state in before.items():
            self.assertEqual(((self.root / path).read_bytes(), (self.root / path).stat().st_mtime_ns), state)
        self.assertFalse(self.fixture.configuration.load().get('ownership_enabled', False))

    def test_private_and_decoded_retired_source_review_cannot_restore_excluded_claims(self):
        self.seed()
        self.forget('SyntheticReviewedVendor')
        relative = 'LIFEOS/USER/FINANCES/vendors.yaml'
        (self.root / relative).write_text('vendors:\n  - id: synthetic\n    name: "SyntheticReviewed\\x56endor"\n')
        private = 'LIFEOS/USER/HEALTH/CONDITIONS.md'
        (self.root / private).write_text('## Conditions\n<private>SyntheticPrivateReviewedCondition</private>\n')
        with httpx.Client(timeout=35) as client:
            self.login(client)
            for path in (relative, private):
                with self.subTest(path=path):
                    snapshot = self.preview(client, [path])
                    self.assertFalse(snapshot['sources'][0]['accepted'], snapshot)
                    self.assertEqual(snapshot['sources'][0]['content'], '')
                    self.assertEqual(self.approve(client, [path], snapshot)['status'], 'rejected')

    def test_source_change_and_new_retirement_invalidate_preview(self):
        self.seed()
        relative = 'LIFEOS/USER/FINANCES/ACCOUNTS.md'
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            path = self.root / relative
            old = path.stat().st_mtime_ns
            path.write_text('## Accounts\nSyntheticChangedReviewedAccount\n')
            os.utime(path, ns=(old, old))
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'conflict')
            fresh = self.preview(client, [relative])
            self.assertEqual(self.approve(client, [relative], fresh)['status'], 'committed')
            self.forget(identifier='synthetic-later-source-review-retirement')
            self.assertEqual(self.approve(client, [relative], fresh)['status'], 'conflict')
            self.assertNotIn('SyntheticChangedReviewedAccount', client.get(self.native + '/api/life/finances').text)

    def test_opaque_metadata_change_invalidates_lab_review(self):
        self.seed()
        self.forget()
        relative = 'LIFEOS/USER/HEALTH/lab_results_2026-10-01.pdf'
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            self.assertNotIn('SyntheticOpaqueLabBody', json.dumps(snapshot))
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'committed')
            self.assertIn('lab_results_2026-10-01.pdf', client.get(self.native + '/api/life/health').text)
            (self.root / relative).write_bytes(b'%PDF-Synthetic changed opaque metadata')
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'conflict')

    def test_anonymous_revoked_and_redirected_sources_cannot_receive_review(self):
        self.seed()
        relative = 'LIFEOS/USER/HEALTH/CONDITIONS.md'
        response = httpx.post(self.dashboard + self.endpoint + '/preview', json={'paths': [relative]})
        self.assertEqual(response.status_code, 401)
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            path = self.root / relative
            external = self.fixture.home / 'synthetic-reviewed-external.md'
            path.rename(external)
            path.symlink_to(external)
            response = client.post(self.dashboard + self.endpoint + '/preview', json={'paths': [relative]})
            self.assertNotEqual(response.status_code, 200)
            self.assertNotIn('SyntheticReviewedCondition', response.text)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            response = client.post(self.dashboard + self.endpoint, json={'paths': [relative], 'signature': snapshot['signature']})
            self.assertEqual(response.status_code, 403)

    def test_project_review_preserves_windows_line_endings_and_restores_native_view(self):
        relative = 'LIFEOS/USER/PROJECTS.md'
        path = self.root / relative
        path.write_bytes(b'## SyntheticWindowsProject\r\nSynthetic project detail\r\n')
        before = path.read_bytes(), path.stat().st_mtime_ns
        self.forget()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            self.assertTrue(snapshot['sources'][0]['accepted'], snapshot)
            self.assertEqual(snapshot['sources'][0]['content'], before[0].decode())
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'committed')
            response = client.get(self.native + '/api/life/work')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/work'))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_retired_lab_metadata_label_cannot_receive_review(self):
        self.seed()
        relative = 'LIFEOS/USER/HEALTH/lab_results_SyntheticRetiredLab.pdf'
        (self.root / relative).write_bytes(b'%PDF-Synthetic opaque report')
        self.forget('SyntheticRetiredLab', 'synthetic-review-lab-label')
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            self.assertFalse(snapshot['sources'][0]['accepted'])
            self.assertEqual(snapshot['sources'][0]['content'], '')
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'rejected')

    def test_malformed_structured_sources_and_foreign_paths_cannot_receive_review(self):
        self.seed()
        relative = 'LIFEOS/USER/FINANCES/state.json'
        (self.root / relative).write_text('synthetic malformed JSON')
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            self.assertFalse(snapshot['sources'][0]['accepted'])
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'rejected')
            for path in ('../outside.md', 'LIFEOS/USER/FINANCES/Tools/SyntheticProgram.ts',
                         'LIFEOS/USER/CONFIG/synthetic-token.json'):
                with self.subTest(path=path):
                    response = client.post(self.dashboard + self.endpoint + '/preview', json={'paths': [path]})
                    self.assertNotEqual(response.status_code, 200)

    def test_hardlinked_source_and_changed_account_cannot_receive_review(self):
        self.seed()
        relative = 'LIFEOS/USER/FINANCES/ACCOUNTS.md'
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            alias = self.fixture.home / 'synthetic-reviewed-account-alias.md'
            os.link(self.root / relative, alias)
            response = client.post(self.dashboard + self.endpoint + '/preview', json={'paths': [relative]})
            self.assertNotEqual(response.status_code, 200)
            alias.unlink()
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            response = client.post(self.dashboard + self.endpoint, json={'paths': [relative], 'signature': snapshot['signature']})
            self.assertEqual(response.status_code, 403)

    def test_restored_identical_lab_metadata_keeps_review_with_a_new_inode(self):
        self.seed()
        self.forget()
        relative = 'LIFEOS/USER/HEALTH/lab_results_2026-10-01.pdf'
        path = self.root / relative
        before = path.stat()
        original = path.read_bytes()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            snapshot = self.preview(client, [relative])
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'committed')
            temporary = self.fixture.home / 'synthetic-restored-lab.pdf'
            temporary.write_bytes(original)
            os.utime(temporary, ns=(before.st_atime_ns, before.st_mtime_ns))
            temporary.replace(path)
            self.assertNotEqual(path.stat().st_ino, before.st_ino)
            response = client.get(self.native + '/api/life/health')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('lab_results_2026-10-01.pdf', response.text)
            self.assertNotIn('SyntheticOpaqueLabBody', response.text)
            self.assertEqual(self.approve(client, [relative], snapshot)['status'], 'unchanged')


if __name__ == '__main__':
    unittest.main()
