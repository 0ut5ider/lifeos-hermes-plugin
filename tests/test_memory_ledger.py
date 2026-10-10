# ABOUTME: Checks the actual native Ledger route against current owner source admission.
# ABOUTME: Preserves native change summaries while refusing stale caches and redirected records.
import json
import os
import unittest

import httpx
from test_memory_native import OWNER
from test_memory_registered_modules import MemoryRegisteredModuleCases


class MemoryLedgerTests(MemoryRegisteredModuleCases, unittest.TestCase):
    native_module = 'ledger.ts'
    route = '/api/ledger'
    source_relative = 'LIFEOS/MEMORY/SYSTEMUPDATES/index.json'
    source_body = {'last_updated': '2026-10-08T00:00:00Z', 'total_updates': 1,
        'by_significance': {'minor': 1}, 'by_change_type': {'fix': 1},
        'updates': [{'timestamp': '2026-10-08T00:00:00Z', 'title': 'MARKER',
            'impact': 'minor', 'type': 'fix', 'version': '0.1.0', 'files_affected': ['synthetic.ts']}]}
    additional_sources = {
        'LIFEOS/MEMORY/SYSTEMUPDATES/deploys.jsonl': '{"ts":"2026-10-08T00:00:00Z","target":"SyntheticDeploy"}\n',
        'LIFEOS/MEMORY/STATE/integrity/last-run.json': '{"ts":"2026-10-08","exitCode":0,"blocking":0,"info":1}',
        'LIFEOS/MEMORY/STATE/integrity/last-pass.json': '{"ts":"2026-10-08","critical":0}',
        'LIFEOS/MEMORY/STATE/version-drift-nag.json': '{"ts":"2026-10-08","count":3,"tag":"0.1.0"}',
        'LIFEOS/VERSION': '0.1.0\n',
        'LIFEOS/ALGORITHM/LATEST': '1.2.3\n',
        'LIFEOS/LIFEOS_SYSTEM_PROMPT.md': '---\nversion: "2.3.4"\n---\n',
    }

    def seed(self, marker='SyntheticRegisteredCurrent'):
        path = MemoryRegisteredModuleCases.seed(self, marker)
        for relative, content in self.additional_sources.items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        return path

    def original(self):
        body = MemoryRegisteredModuleCases.original(self)
        body.pop('generated_at')
        return body

    def test_original_native_sources_absence_and_malformed_json_characterization(self):
        path = self.seed()
        body = self.original()
        self.assertEqual(body['registry']['recent'][0]['title'], 'SyntheticRegisteredCurrent')
        self.assertEqual(body['versions'], {'lifeos': '0.1.0', 'algorithm': '1.2.3', 'system_prompt': '2.3.4'})
        self.assertTrue(body['integrity']['clean'])
        self.assertEqual(body['deploys'][0]['target'], 'SyntheticDeploy')
        path.unlink()
        self.assertIsNone(self.original()['registry'])
        path.write_text('{"updates":')
        self.assertIsNone(self.original()['registry'])

    def test_admitted_fields_and_absence_preserve_actual_native_response(self):
        path = self.seed()
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for missing in (False, True):
                if missing:
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
                    path.unlink()
                for suffix in ('', '/'):
                    response = client.get(self.native + self.route + suffix)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    body = response.json()
                    body.pop('generated_at')
                    self.assertEqual(body, self.original())
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_exact_review_restores_only_current_safe_old_source(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated Ledger retirement',
            title='', project='', request_id='ledger-review-unrelated')
        memory.forget(OWNER, saved['reference'], 'ledger-review-unrelated-forget')
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
        self.assertEqual([((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns) for relative in relatives], before)

    def test_native_recent_slices_and_total_rollups_are_preserved(self):
        path = self.seed()
        body = json.loads(path.read_text())
        body['total_updates'] = 47
        body['updates'] = [dict(body['updates'][0], title='SyntheticLedgerUpdate' + str(i)) for i in range(47)]
        path.write_text(json.dumps(body))
        deploys = self.root / 'LIFEOS/MEMORY/SYSTEMUPDATES/deploys.jsonl'
        deploys.write_text(''.join(json.dumps({'target': 'SyntheticDeploy' + str(i)}) + '\n' for i in range(47)))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text[:300])
            result = response.json()
            result.pop('generated_at')
            self.assertEqual(result, self.original())
            self.assertEqual(result['registry']['total_updates'], 47)
            self.assertEqual(len(result['registry']['recent']), 40)
            self.assertEqual(len(result['deploys']), 40)
            self.assertEqual(result['deploys'][0]['target'], 'SyntheticDeploy46')

    def test_decoded_private_deploy_source_cannot_reuse_registry_cache(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            path = self.root / 'LIFEOS/MEMORY/SYSTEMUPDATES/deploys.jsonl'
            text = json.dumps({'nested': json.dumps({'label': '<private>SyntheticLedgerHidden</private>'})})
            path.write_text(text.replace('<', '\\u003c').replace('>', '\\u003e') + '\n')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticLedgerHidden', response.text)


if __name__ == '__main__': unittest.main()
