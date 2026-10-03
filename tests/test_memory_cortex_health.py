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

    def call(self, *, context=True, root=None, now=None, filter_assessment=False):
        source = str(self.root / 'LIFEOS/TOOLS/CortexHealth.ts')
        code = ('const m=await import(' + json.dumps(source) + '); try {'
                'const evidence=m.collectCortexEvidence({root:' + json.dumps(str(root or self.root))
                + (',nowMs:Date.parse(' + json.dumps(now) + ')' if now else '') + '});'
                'let assessment=m.assessCortexEvidence(evidence);'
                + ('const a=await import(' + json.dumps(str(self.root / 'LIFEOS/TOOLS/lib/MemoryAccess.ts')) + ');'
                   'assessment=a.filterMemoryDiagnostic(assessment,new Date().toISOString());' if filter_assessment else '') +
                'console.log(JSON.stringify({evidence, assessment}));'
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

    def health(self, *, context=True, timeout=45, report_path=None, clock=None, expected_error=None,
               max_observability_bytes=None):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for key in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'CORTEX_HEALTH_ROOT', 'CORTEX_INDEX_MANIFEST',
                    'CORTEX_HEALTH_NOW', 'CORTEX_HEALTH_NO_WRITE', 'CORTEX_HEALTH_REPORT_PATH',
                    'CORTEX_OBSERVABILITY_MAX_BYTES'):
            environment.pop(key, None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        if report_path is not None:
            environment['CORTEX_HEALTH_REPORT_PATH'] = str(report_path)
        if clock is not None:
            environment['CORTEX_HEALTH_NOW'] = clock
        if max_observability_bytes is not None:
            environment['CORTEX_OBSERVABILITY_MAX_BYTES'] = str(max_observability_bytes)
        result = subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/MemoryHealthCheck.ts')],
                                env=environment, cwd=self.root, capture_output=True, text=True, timeout=timeout)
        if expected_error is not None:
            self.assertIn(expected_error, result.stderr)
            self.assertEqual(result.stdout, '')
            return result, None
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

    def retire_fields(self, fields):
        for field in fields:
            saved = self.fixture.fixture.remember('RULE: ' + field, 'schema-' + field, 'principal')
            self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-schema-' + field)

    def test_retired_marker_field_preserves_native_critical_report_and_publication(self):
        self.retire_fields(('begins', 'ends', 'inverted'))
        path = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        path.write_text(path.read_text().replace('<!-- END ENTRIES -->', '<!-- END ENTRIES -->\n<!-- END ENTRIES -->'))
        result, report = self.health()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['overall'], 'critical')
        marker = next(row for row in report['findings'] if row['id'] == 'markers-corrupt:principal')
        self.assertEqual(marker['detail'], {'begins': 1, 'ends': 2, 'inverted': False})
        self.assertEqual(json.loads((self.obs / 'memory-health.jsonl').read_text().splitlines()[-1]), report)

    def test_retired_settings_field_names_preserve_native_missing_hook_report(self):
        self.retire_fields(('system', 'live'))
        (self.root / 'settings.system.json').write_text(json.dumps({'hooks': ['MemoryTurnStart.hook.ts']}))
        result, report = self.health()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('unavailable', report)
        finding = next(row for row in report['findings'] if row['id'].startswith('settings-hook-missing'))
        self.assertEqual(finding['severity'], 'critical')
        self.assertEqual(set(finding['detail']), {'system', 'live', 'hook'})
        self.assertEqual(finding['detail']['live'], str(self.root / 'settings.json'))
        self.assertEqual(finding['detail']['hook'], 'MemoryTurnStart.hook.ts')
        self.assertIsInstance(finding['detail']['system'], str)
        self.assertNotIn('settings.system.json', finding['detail']['system'])
        self.assertEqual(json.loads((self.obs / 'memory-health.jsonl').read_text().splitlines()[-1]), report)

    def test_retired_state_and_cortex_field_names_preserve_native_report(self):
        self.retire_fields(('hook', 'turn_count', 'last_review_at', 'pending_review', 'age_days',
                            'staleThresholdMs', 'thresholdMs', 'files', 'bytes', 'available', 'maxBytes'))
        (self.obs / 'review-state.json').write_text(json.dumps({'last_review_at': '2020-01-01T00:00:00Z',
            'turn_count_since_last_review': 7, 'pending_review': True}))
        result, report = self.health(max_observability_bytes=1)
        self.assertNotIn('unavailable', report)
        by_id = {row['id']: row for row in report['findings']}
        self.assertIn('state-readable', report['ok_summary'])
        hook = next(row for row in report['findings'] if 'hook' in row.get('detail', {}))
        self.assertIsInstance(hook['detail']['hook'], str)
        self.assertEqual(by_id['review-stale']['detail']['last_review_at'], '2020-01-01T00:00:00Z')
        self.assertEqual(by_id['reviewer-evidence-missing']['detail']['staleThresholdMs'], 604800000)
        self.assertEqual(by_id['retrieval-missing']['detail']['thresholdMs'], 86400000)
        observability = next(row['detail'] for row in report['findings'] if 'maxBytes' in row.get('detail', {}))
        self.assertGreater(observability['files'], 0)
        self.assertGreater(observability['bytes'], 1)
        self.assertTrue(observability['available'])
        self.assertEqual(observability['maxBytes'], 1)
        self.assertEqual(json.loads((self.obs / 'memory-health.jsonl').read_text().splitlines()[-1]), report)

    def test_declared_health_detail_fields_do_not_exempt_nested_content_keys(self):
        from lifeos_hook_bridge.memory_diagnostics import filter_report
        self.retire_fields(('begins',))
        report = {'findings': [{'detail': {'begins': 1, 'nested': {'begins': 'unrelated control'},
            'error': {'begins': 'other control'}, 'content': 'begins'}}]}
        projected = filter_report(self.fixture.fixture.memory, OWNER, json.dumps(report),
                                  datetime.now(timezone.utc).isoformat())
        detail = json.loads(projected['content'])['findings'][0]['detail']
        self.assertEqual(detail['begins'], 1)
        self.assertEqual(detail['nested'], {})
        self.assertEqual(detail['error'], {})
        self.assertNotIn('begins', detail['content'])

    def test_retired_invalid_entry_field_names_preserve_native_warning(self):
        self.retire_fields(('entry', 'reason'))
        path = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        entry = 'RULE: Synthetic overlength health row' + ' x' * 150
        path.write_text(path.read_text().replace('<!-- END ENTRIES -->',
            entry + '\n<!-- END ENTRIES -->'))
        result, report = self.health()
        self.assertNotIn('unavailable', report)
        warning = next(row for row in report['findings'] if row['id'] == 'pending-silent-loss:principal')
        self.assertEqual(warning['detail']['dropped'],
                         [{'entry': entry, 'reason': 'overlength'}])
        self.assertEqual(json.loads((self.obs / 'memory-health.jsonl').read_text().splitlines()[-1]), report)

    def test_native_cortex_assessment_evidence_preserves_retired_schema_field_names(self):
        self.retire_fields(('staleThresholdMs', 'thresholdMs', 'files', 'available'))
        (self.obs / 'memory-writes.jsonl').unlink(missing_ok=True)
        result = self.call(filter_assessment=True)
        self.assertNotIn('unavailable', result)
        self.assertEqual(result['assessment']['overall'], 'warn')
        details = [row['evidence'] for row in result['assessment']['findings'] if 'evidence' in row]
        self.assertEqual(next(row for row in details if 'staleThresholdMs' in row)['staleThresholdMs'], 604800000)
        self.assertEqual(next(row for row in details if 'thresholdMs' in row)['thresholdMs'], 86400000)
        observability = next(row for row in details if 'files' in row)
        self.assertEqual(observability['files'], 0)
        self.assertFalse(observability['available'])

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

    def test_optional_report_cannot_overwrite_configuration_or_publish_a_log(self):
        target = self.root / 'LIFEOS/USER/CONFIG/synthetic-protected-output.json'
        target.write_text('Synthetic configuration sentinel\n')
        result, report = self.health(report_path=target)
        self.assertEqual(target.read_text(), 'Synthetic configuration sentinel\n')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report, {'unavailable': 'Memory diagnostics are unavailable under the current policy'})
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_optional_report_in_diagnostic_directory_matches_stdout_and_log(self):
        target = self.obs / 'reports/synthetic-owner-report.json'
        self.reviewer('Synthetic current report destination control')
        result, report = self.health(report_path=target)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(target.read_text()), report)
        self.assertEqual(json.loads((self.obs / 'memory-health.jsonl').read_text()), report)

    def test_optional_report_redirect_cannot_overwrite_configuration(self):
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-report-secret.json'
        secret.write_text('Synthetic report sentinel\n')
        directory = self.obs / 'reports'
        directory.mkdir()
        target = directory / 'synthetic-report.json'
        target.symlink_to(secret)
        result, report = self.health(report_path=target)
        self.assertEqual(secret.read_text(), 'Synthetic report sentinel\n')
        self.assertIn('unavailable', report)
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_unmanaged_optional_report_keeps_native_destination_behavior(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        target = self.fixture.fixture.home / 'synthetic-unmanaged-report.json'
        result, report = self.health(context=False, report_path=target)
        self.assertEqual(json.loads(target.read_text()), report)

    def test_retired_operational_clock_does_not_change_reviewer_assessment(self):
        stamp = self.now
        saved = self.fixture.fixture.remember('RULE: ' + stamp, 'clock', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-clock')
        (self.obs / 'reviewer-runs.jsonl').write_text(json.dumps({'ts': stamp, 'ok': True,
            'runId': 'synthetic-current-run', 'exchanges': 0, 'inference_duration_ms': 0,
            'parse_ok': True, 'skipped': True}) + '\n')
        managed = self.call(now=stamp)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        unmanaged = self.call(context=False, now=stamp)
        self.assertEqual(managed['evidence']['reviewer']['ts'], stamp)
        self.assertEqual(managed['assessment']['overall'], unmanaged['assessment']['overall'])
        self.assertEqual(managed['assessment']['thresholds'], unmanaged['assessment']['thresholds'])
        self.assertEqual([(row['id'], row['severity']) for row in managed['assessment']['findings']],
                         [(row['id'], row['severity']) for row in unmanaged['assessment']['findings']])

    def test_retired_clock_text_in_error_is_still_filtered(self):
        stamp = self.now
        saved = self.fixture.fixture.remember('RULE: ' + stamp, 'clock-text', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-clock-text')
        self.reviewer(stamp)
        evidence = self.call()['evidence']['reviewer']
        self.assertEqual(evidence['ts'], stamp)
        self.assertNotIn(stamp, evidence['error'])

    def test_large_invalid_hot_report_preserves_all_native_warnings_under_deadline(self):
        self.reviewer('Synthetic current report volume control')
        hot = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        entries = ['RULE: Synthetic overlength diagnostic ' + str(index) + ' x' * 160 for index in range(500)]
        hot.write_text(hot.read_text().replace('<!-- END ENTRIES -->', '\n'.join(entries) + '\n<!-- END ENTRIES -->'))
        managed_result, managed = self.health(timeout=5)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        unmanaged_result, unmanaged = self.health(context=False, timeout=5)
        self.assertEqual(managed_result.returncode, unmanaged_result.returncode)
        self.assertEqual(managed['counts'], unmanaged['counts'])
        self.assertEqual(managed['overall'], unmanaged['overall'])
        for report in (managed, unmanaged):
            warning = next(row for row in report['findings'] if row['id'] == 'pending-silent-loss:principal')
            self.assertEqual(len(warning['detail']['dropped']), 500)
            self.assertEqual(warning['severity'], 'warn')

    def rpc(self, operation, arguments):
        connector = json.loads((self.root / 'LIFEOS/USER/CONFIG/memory-access.json').read_text())
        result = subprocess.run(connector['command'],
            input=json.dumps({'operation': operation, 'arguments': arguments}), text=True,
            capture_output=True, env=dict(os.environ, LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(self.fixture.context))),
            timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_diagnostic_rpc_refuses_requests_above_three_mebibytes_cleanly(self):
        result = self.rpc('filter_diagnostic', {'content': 'x' * (3 * 1024 * 1024), 'timestamp': self.now})
        self.assertFalse(result['ok'])
        self.assertEqual(result['message'], 'The native memory request exceeds the input limit')
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_other_rpc_operations_keep_the_smaller_byte_limit(self):
        result = self.rpc('filter_source', {'content': 'x' * 131072, 'timestamp': self.now})
        self.assertFalse(result['ok'])
        self.assertEqual(result['message'], 'The native memory request exceeds the input limit')

    def test_report_clock_exemption_requires_a_valid_structural_timestamp(self):
        stamp = self.now
        saved = self.fixture.fixture.remember('RULE: ' + stamp, 'clock-fields', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-clock-fields')
        fields = {'ts': stamp, 'timestamp': stamp, 'created_at': stamp, 'last_review_at': stamp,
                  'last_message_at': stamp, 'error': stamp, 'content': stamp, 'other': stamp,
                  'invalid': {'ts': 'Invalid clock ' + stamp}}
        result = self.rpc('filter_diagnostic', {'content': json.dumps(fields), 'timestamp': self.now})
        self.assertTrue(result['ok'], result)
        report = json.loads(result['content'])
        for key in ('ts', 'timestamp', 'created_at', 'last_review_at', 'last_message_at'):
            self.assertEqual(report[key], stamp)
        for key in ('error', 'content', 'other'):
            self.assertNotIn(stamp, report[key])
        self.assertNotIn(stamp, report['invalid']['ts'])

    def test_report_filter_refuses_a_serialized_response_above_its_wire_limit(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        fields = {'samples': ['x' * 65000 + str(index) for index in range(50)]}
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'filter_diagnostic',
                    {'content': json.dumps(fields), 'timestamp': self.now})
        self.assertFalse(result['ok'])
        self.assertEqual(result['message'], 'The diagnostic projection exceeds the native response limit')

    def test_optional_report_cannot_replace_an_existing_diagnostic_input(self):
        target = self.obs / 'review-state.json'
        sentinel = json.dumps({'pending_review': True, 'turn_count_since_last_review': 4})
        target.write_text(sentinel)
        result, report = self.health(report_path=target)
        self.assertEqual(target.read_text(), sentinel)
        self.assertIn('unavailable', report)
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_oversized_native_health_report_returns_unavailable_without_publication(self):
        self.reviewer('Synthetic oversized health report control')
        hot = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        entries = ['RULE: Synthetic large invalid entry ' + str(index) + ' x' * 160 for index in range(8000)]
        hot.write_text(hot.read_text().replace('<!-- END ENTRIES -->', '\n'.join(entries) + '\n<!-- END ENTRIES -->'))
        target = self.obs / 'reports/synthetic-oversized.json'
        result, report = self.health(timeout=15, report_path=target)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report, {'unavailable': 'Memory diagnostics are unavailable under the current policy'})
        self.assertFalse(target.exists())
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_nested_clock_fields_inside_native_errors_remain_filtered(self):
        stamp = self.now
        saved = self.fixture.fixture.remember('RULE: ' + stamp, 'nested-clock', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-nested-clock')
        self.now = datetime.now(timezone.utc).isoformat()
        self.reviewer({'ts': stamp, 'message': stamp, 'content': {'timestamp': stamp}})
        evidence = self.call()['evidence']['reviewer']
        self.assertNotIn(stamp, json.dumps(evidence['error']))
        self.assertEqual(evidence['ts'], self.now)
        result, report = self.health()
        self.assertNotIn(stamp, json.dumps(report))
        self.assertNotIn(stamp, (self.obs / 'memory-health.jsonl').read_text())

    def test_enum_exemption_does_not_apply_inside_error_or_detail_content(self):
        saved = self.fixture.fixture.remember('RULE: critical', 'enum-field', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-enum-field')
        fields = {'overall': 'critical', 'findings': [{'severity': 'critical', 'message': 'critical',
                   'detail': {'severity': 'critical', 'overall': 'critical'}}],
                  'error': {'overall': 'critical', 'severity': 'critical'}}
        result = self.rpc('filter_diagnostic', {'content': json.dumps(fields),
                                               'timestamp': datetime.now(timezone.utc).isoformat()})
        self.assertTrue(result['ok'], result)
        report = json.loads(result['content'])
        self.assertEqual(report['overall'], 'critical')
        self.assertEqual(report['findings'][0]['severity'], 'critical')
        self.assertNotIn('critical', json.dumps(report['error']))
        self.assertNotIn('critical', json.dumps(report['findings'][0]['detail']))
        self.assertNotIn('critical', report['findings'][0]['message'])

    def test_unmanaged_invalid_clock_retains_native_exception_semantics(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result, report = self.health(context=False, clock='invalid-synthetic-clock', expected_error='RangeError')
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())

    def test_managed_invalid_clock_is_unavailable_without_publication(self):
        result, report = self.health(clock='invalid-synthetic-clock')
        self.assertEqual(result.returncode, 2)
        self.assertIn('unavailable', report)
        self.assertFalse((self.obs / 'memory-health.jsonl').exists())
