# ABOUTME: Checks governed Cortex evidence without losing native health decisions.
# ABOUTME: Runs real collectors and assessments against isolated reviewer diagnostics.

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryCortexHealthTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.obs = self.root / 'LIFEOS/MEMORY/OBSERVABILITY'
        self.obs.mkdir(parents=True, exist_ok=True)
        self.now = datetime.now(timezone.utc).isoformat()

    def reviewer(self, error):
        (self.obs / 'reviewer-runs.jsonl').write_text(json.dumps({'ts': self.now, 'ok': False,
            'parse_ok': False, 'runId': '2026-09-30T23-55-00-000Z', 'error': error}) + '\n')

    def call(self, *, context=True, root=None):
        source = str(self.root / 'LIFEOS/TOOLS/CortexHealth.ts')
        code = ('const m=await import(' + json.dumps(source) + '); try {'
                'const evidence=m.collectCortexEvidence({root:' + json.dumps(str(root or self.root)) + '});'
                'console.log(JSON.stringify({evidence, assessment:m.assessCortexEvidence(evidence)}));'
                '} catch {console.log(JSON.stringify({unavailable:true}));}')
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        result = subprocess.run(['bun', '--no-install', '-e', code], env=environment, cwd=self.root,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_owner_failed_reviewer_remains_critical_and_preserves_current_error(self):
        self.reviewer('Synthetic current parse failure')
        result = self.call()
        self.assertEqual(result['evidence']['reviewer']['status'], 'parse-failed')
        self.assertEqual(result['assessment']['overall'], 'critical')
        self.assertIn('Synthetic current parse failure', json.dumps(result))

    def test_unmanaged_reviewer_retains_native_error(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.reviewer('Synthetic unmanaged Cortex error')
        self.assertIn('Synthetic unmanaged Cortex error', json.dumps(self.call(context=False)))

    def test_missing_context_refuses_all_cortex_evidence(self):
        self.reviewer('Synthetic private Cortex error')
        self.assertEqual(self.call(context=False), {'unavailable': True})

    def test_retired_error_is_excluded_without_losing_critical_status(self):
        saved = self.fixture.fixture.remember('RULE: Synthetic retired Cortex error', 'cortex', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-cortex')
        self.now = datetime.now(timezone.utc).isoformat()
        self.reviewer('Synthetic retired Cortex error')
        result = self.call()
        self.assertNotIn('Synthetic retired Cortex error', json.dumps(result))
        self.assertEqual(result['evidence']['reviewer']['status'], 'parse-failed')
        self.assertEqual(result['assessment']['overall'], 'critical')

    def test_malformed_reviewer_preserves_parse_failure_and_line_numbers(self):
        self.reviewer('Synthetic valid predecessor')
        with (self.obs / 'reviewer-runs.jsonl').open('a') as stream:
            stream.write('{malformed\n')
        result = self.call()
        self.assertEqual(result['evidence']['reviewer']['status'], 'parse-failed')
        self.assertIn('malformed JSONL lines: 2', json.dumps(result))
        self.assertEqual(result['assessment']['overall'], 'critical')

    def test_explicit_other_root_cannot_bypass_managed_memory(self):
        self.reviewer('Synthetic bound Cortex error')
        other = self.fixture.fixture.home / 'other'
        (other / 'LIFEOS/MEMORY/OBSERVABILITY').mkdir(parents=True)
        (other / 'LIFEOS/MEMORY/OBSERVABILITY/reviewer-runs.jsonl').write_text(json.dumps(
            {'ts': self.now, 'ok': False, 'error': 'Synthetic alternate root error'}) + '\n')
        self.assertEqual(self.call(root=other), {'unavailable': True})

    def test_reviewer_redirect_cannot_read_configuration(self):
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-cortex-secret.json'
        secret.write_text(json.dumps({'ts': self.now, 'ok': False, 'error': 'Synthetic Cortex secret'}) + '\n')
        (self.obs / 'reviewer-runs.jsonl').symlink_to(secret)
        self.assertEqual(self.call(), {'unavailable': True})

    def test_malformed_latest_reviewer_keeps_invalid_status_without_undefined_shape_failure(self):
        (self.obs / 'reviewer-runs.jsonl').write_text(json.dumps({'ok': True}) + '\n')
        result = self.call()
        self.assertEqual(result['evidence']['reviewer']['status'], 'invalid')
        self.assertEqual(result['assessment']['overall'], 'critical')

    def test_json_encoded_retired_error_is_excluded_before_diagnostic_delivery(self):
        saved = self.fixture.fixture.remember('RULE: Synthetic encoded retired Cortex error', 'encoded', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-encoded-cortex')
        self.now = datetime.now(timezone.utc).isoformat()
        encoded = ''.join('\\u%04x' % ord(character) for character in 'Synthetic encoded retired Cortex error')
        self.reviewer('{"message":"' + encoded + '"}')
        result = self.call()
        error = result['evidence']['reviewer']['error']
        self.assertNotIn(encoded, error)
        self.assertNotIn('Synthetic encoded retired Cortex error', error)
        self.assertEqual(result['assessment']['overall'], 'critical')

    def health(self, *, context=True, timeout=45):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for key in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'CORTEX_HEALTH_ROOT', 'CORTEX_INDEX_MANIFEST',
                    'CORTEX_HEALTH_NOW', 'CORTEX_HEALTH_NO_WRITE', 'CORTEX_HEALTH_REPORT_PATH'):
            environment.pop(key, None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        result = subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/MemoryHealthCheck.ts')],
                                env=environment, cwd=self.root, capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.stderr, '')
        return result, json.loads(result.stdout)

    def test_owner_health_report_keeps_current_failure_and_native_publication(self):
        self.reviewer('Synthetic current published health error')
        result, report = self.health()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['overall'], 'critical')
        self.assertGreater(report['counts']['critical'], 0)
        self.assertIn('Synthetic current published health error', json.dumps(report))
        published = json.loads((self.obs / 'memory-health.jsonl').read_text().splitlines()[-1])
        self.assertEqual(published, report)

    def test_missing_identity_does_not_publish_health_as_a_new_diagnostic(self):
        self.reviewer('Synthetic private published health error')
        result, report = self.health(context=False)
        self.assertEqual(report, {'unavailable': 'Memory diagnostics are unavailable under the current policy'})
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_final_health_report_excludes_retired_state_strings_before_writing(self):
        saved = self.fixture.fixture.remember('RULE: Synthetic retired health state marker', 'health-state', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-health-state')
        self.reviewer('Synthetic current health report failure')
        (self.obs / 'review-state.json').write_text(json.dumps({'last_review_at': 'Synthetic retired health state marker',
                                                               'turn_count_since_last_review': 5, 'pending_review': True}))
        result, report = self.health()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['overall'], 'critical')
        self.assertNotIn('Synthetic retired health state marker', json.dumps(report))
        self.assertIn('Synthetic current health report failure', json.dumps(report))
        self.assertNotIn('Synthetic retired health state marker', (self.obs / 'memory-health.jsonl').read_text())

    def test_final_health_report_filters_retired_invalid_entry_without_losing_warning(self):
        marker = 'Synthetic retired invalid health entry'
        saved = self.fixture.fixture.remember('RULE: ' + marker, 'health-invalid', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-health-invalid')
        hot = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        hot.write_text(hot.read_text().replace('<!-- END ENTRIES -->', 'RULE: ' + marker + ' x' * 150 + '\n<!-- END ENTRIES -->'))
        self.reviewer('Synthetic current health report error')
        result, report = self.health()
        self.assertEqual(result.returncode, 2)
        warning = next(row for row in report['findings'] if row['id'] == 'pending-silent-loss:principal')
        self.assertEqual(warning['severity'], 'warn')
        self.assertEqual(len(warning['detail']['dropped']), 1)
        self.assertNotIn(marker, json.dumps(report))
        self.assertNotIn(marker, (self.obs / 'memory-health.jsonl').read_text())

    def test_redirected_health_output_does_not_change_configuration(self):
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-health-output.json'
        secret.write_text('Synthetic configuration must stay unchanged\n')
        (self.obs / 'memory-health.jsonl').symlink_to(secret)
        result, report = self.health()
        self.assertEqual(report, {'unavailable': 'Memory diagnostics are unavailable under the current policy'})
        self.assertEqual(secret.read_text(), 'Synthetic configuration must stay unchanged\n')

    def test_owner_missing_hot_file_remains_an_explicit_critical_finding(self):
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md').unlink()
        result, report = self.health()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['overall'], 'critical')
        finding = next(row for row in report['findings'] if row['id'] == 'principal-memory-missing')
        self.assertEqual(finding['severity'], 'critical')

    def test_owner_health_report_finishes_under_native_gate_deadline(self):
        self.reviewer('Synthetic owner deadline control')
        result, report = self.health(timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['overall'], 'critical')

    def test_reviewer_directory_redirect_cannot_become_memory_evidence(self):
        target = self.root / 'LIFEOS/USER/CONFIG/synthetic-private-runs'
        run = target / '2026-09-30T23-55-00-000Z'
        run.mkdir(parents=True)
        (run / 'parse-error.txt').write_text('Synthetic configuration-only run marker')
        (self.obs / 'reviewer-runs').symlink_to(target)
        self.assertEqual(self.call(), {'unavailable': True})

    def test_index_directory_redirect_cannot_become_memory_evidence(self):
        target = self.root / 'LIFEOS/USER/CONFIG/synthetic-private-index'
        target.mkdir()
        (target / 'index-manifest.json').write_text('{}')
        (self.root / 'LIFEOS/MEMORY/INDEX').symlink_to(target)
        self.assertEqual(self.call(), {'unavailable': True})
