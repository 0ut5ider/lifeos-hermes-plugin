# ABOUTME: Exercises native memory status and insights with governed diagnostic records.
# ABOUTME: Preserves operational counts while refusing unavailable scope and retired text.

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.obs = self.root / 'LIFEOS/MEMORY/OBSERVABILITY'
        self.obs.mkdir(parents=True, exist_ok=True)
        self.now = datetime.now(timezone.utc).isoformat()

    def write(self, name, rows):
        path = self.obs / name
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return path

    def call(self, tool, *arguments, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        result = subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS' / tool), *arguments],
                                env=environment, cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.stderr, '')
        return result

    def reviewer(self, **fields):
        return {'ts': self.now, 'ok': False, 'duration_ms': 37,
                'items_total': 2, 'inference_duration_ms': 41, **fields}

    def proposal(self, edit, **fields):
        return {'id': 'synthetic-proposal', 'ts': self.now, 'status': 'pending',
                'target_kind': 'identity', 'target_file': 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
                'edit': edit, **fields}

    def retire(self, marker):
        saved = self.fixture.fixture.remember('RULE: ' + marker, 'diagnostic', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-diagnostic')
        self.now = datetime.now(timezone.utc).isoformat()

    def test_owner_status_preserves_current_operational_fields(self):
        self.write('reviewer-runs.jsonl', [self.reviewer()])
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic current diagnostic edit')])
        result = self.call('MemoryStatus.ts', '--json')
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report['last_reviewer_run']['duration_ms'], 37)
        self.assertFalse(report['last_reviewer_run']['ok'])
        self.assertEqual(report['proposals']['pending'], 1)

    def test_owner_insights_preserves_latency_counts_and_current_sample(self):
        self.write('reviewer-runs.jsonl', [self.reviewer(ok=True)])
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic current diagnostic edit')])
        result = self.call('MemoryInsights.ts', '--days', '7')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Synthetic current diagnostic edit', result.stdout)
        self.assertIn('p95 latency 41ms', result.stdout)
        self.assertIn('Reviewer runs (1 total)', result.stdout)

    def test_unmanaged_status_keeps_native_raw_diagnostic_behavior(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.write('reviewer-runs.jsonl', [self.reviewer(error='Synthetic unmanaged diagnostic error')])
        self.assertIn('Synthetic unmanaged diagnostic error', self.call('MemoryStatus.ts', '--json', context=False).stdout)

    def test_unmanaged_insights_keeps_native_proposal_sample(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic unmanaged proposal')])
        self.assertIn('Synthetic unmanaged proposal', self.call('MemoryInsights.ts', context=False).stdout)

    def test_missing_context_refuses_diagnostics_and_reports_unavailability(self):
        self.write('reviewer-runs.jsonl', [self.reviewer(error='Synthetic private diagnostic marker')])
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic private diagnostic marker')])
        for tool, arguments in (('MemoryStatus.ts', ('--json',)), ('MemoryInsights.ts', ())):
            with self.subTest(tool=tool):
                result = self.call(tool, *arguments, context=False)
                self.assertIn('unavailable', result.stdout.lower())
                self.assertNotIn('Synthetic private diagnostic marker', result.stdout)
                self.assertNotIn('Reviewer runs (1 total)', result.stdout)

    def test_retired_diagnostic_text_is_excluded_but_failure_count_remains(self):
        self.retire('Synthetic retired diagnostic claim')
        path = self.write('reviewer-runs.jsonl', [self.reviewer(error='Synthetic retired diagnostic claim',
                                                              content='Synthetic retired diagnostic claim')])
        before = path.read_bytes()
        result = self.call('MemoryStatus.ts', '--json')
        report = json.loads(result.stdout)
        self.assertNotIn('Synthetic retired diagnostic claim', result.stdout)
        self.assertFalse(report['last_reviewer_run']['ok'])
        self.assertEqual(report['last_reviewer_run']['items_total'], 2)
        self.assertEqual(path.read_bytes(), before)

    def test_retired_proposal_samples_do_not_remove_queue_statistics(self):
        self.retire('Synthetic retired proposal claim')
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic retired proposal claim'),
                                                self.proposal('Synthetic current proposal control', id='current')])
        result = self.call('MemoryInsights.ts')
        self.assertNotIn('Synthetic retired proposal claim', result.stdout)
        self.assertIn('Synthetic current proposal control', result.stdout)
        self.assertIn('Proposals (2 total in window)', result.stdout)

    def test_invalid_connector_refuses_diagnostics_without_raw_fallback(self):
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic invalid connector claim')])
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').write_text('{invalid')
        result = self.call('MemoryInsights.ts')
        self.assertIn('unavailable', result.stdout.lower())
        self.assertNotIn('Synthetic invalid connector claim', result.stdout)

    def test_restricted_or_changed_context_cannot_read_diagnostic_counts(self):
        self.write('reviewer-runs.jsonl', [self.reviewer()])
        original = self.fixture.context
        for context in (replace(original, author='unknown'), replace(original, participants=('other',))):
            self.fixture.context = context
            result = self.call('MemoryStatus.ts', '--json')
            self.assertIn('unavailable', result.stdout.lower())
            self.assertNotIn('items_total', result.stdout)
        self.fixture.context = original
        configuration = self.fixture.configuration.load()
        configuration['destinations']['chat-a:200'].update(read=['project'], projects=['lab'])
        self.fixture.configuration.save(configuration)
        self.assertIn('unavailable', self.call('MemoryInsights.ts').stdout.lower())

    def test_diagnostic_file_redirect_refuses_secret_and_preserves_unavailable_state(self):
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-secret.json'
        secret.write_text(json.dumps(self.reviewer(content='Synthetic configuration secret')) + '\n')
        (self.obs / 'reviewer-runs.jsonl').symlink_to(secret)
        result = self.call('MemoryStatus.ts', '--json')
        self.assertIn('unavailable', result.stdout.lower())
        self.assertNotIn('Synthetic configuration secret', result.stdout)

    def test_insights_retains_full_requested_window_beyond_delta_tail(self):
        self.write('reviewer-runs.jsonl', [self.reviewer(ok=True)] * 1001)
        result = self.call('MemoryInsights.ts', '--days', '7')
        self.assertIn('Reviewer runs (1001 total)', result.stdout)
        self.assertIn('p95 latency 41ms', result.stdout)

    def test_latest_invalid_reviewer_row_does_not_replay_previous_success(self):
        self.write('reviewer-runs.jsonl', [self.reviewer(ok=True), {'ts': self.now, 'ok': 'true',
                                                                  'content': 'Synthetic invalid row content'}])
        result = self.call('MemoryStatus.ts', '--json')
        report = json.loads(result.stdout)
        self.assertNotIn('Synthetic invalid row content', result.stdout)
        self.assertIsNone(report['last_reviewer_run'].get('ok'))

    def test_native_proposal_subtypes_and_terminal_counts_keep_their_meaning(self):
        self.write('pending-proposals.jsonl', [self.proposal('Synthetic style edit', target_kind='style'),
                                                self.proposal('Synthetic resolved edit', status='auto-applied'),
                                                self.proposal('Synthetic surfaced edit', status='sent')])
        report = json.loads(self.call('MemoryStatus.ts', '--json').stdout)
        self.assertEqual(report['proposals']['pending'], 1)
        self.assertEqual(report['proposals']['pending_by_kind'], {'style': 1})
        output = self.call('MemoryInsights.ts').stdout
        self.assertIn('auto-applied', output)
        self.assertIn('sent', output)

    def test_malformed_diagnostic_values_cannot_crash_or_print_object_contents(self):
        self.write('pending-proposals.jsonl', [self.proposal({'secret': 'Synthetic malformed edit'},
                                    status={'secret': 'Synthetic malformed status'}, target_kind=['Synthetic malformed kind'])])
        self.write('reviewer-runs.jsonl', [self.reviewer(ok='true', duration_ms=True, inference_duration_ms=-1)])
        output = self.call('MemoryInsights.ts').stdout
        self.assertNotIn('Synthetic malformed', output)
        self.assertIn('Reviewer runs (1 total)', output)
        self.assertNotIn('unavailable', output)

    def test_safe_numeric_growth_and_health_stay_available_after_retirement(self):
        self.retire('Synthetic retired metric detail')
        self.write('memory-writes.jsonl', [{'ts': self.now, 'file': 'PRINCIPAL_MEMORY.md',
                  'new_count': 7, 'prior_count': 3, 'additions': ['Synthetic retired metric detail']}])
        self.write('memory-health.jsonl', [{'ts': self.now, 'overall': 'critical',
                  'counts': {'critical': 2, 'warn': 1, 'ok': 4}, 'error': 'Synthetic retired metric detail'}])
        output = self.call('MemoryInsights.ts').stdout
        self.assertIn('+4 entries', output)
        self.assertIn('critical=2 warn=1 ok=4', output)
        self.assertIn('Verdict: unhealthy', output)
        self.assertNotIn('Synthetic retired metric detail', output)

    def test_review_state_discards_arbitrary_strings_and_preserves_typed_values(self):
        self.write('review-state.json', [])
        (self.obs / 'review-state.json').write_text(json.dumps({'turn_count_since_last_review': 9,
                  'pending_review': True, 'last_review_at': self.now, 'last_message_at': 'Synthetic arbitrary state text'}))
        output = self.call('MemoryStatus.ts', '--json').stdout
        state = json.loads(output)['review_state']
        self.assertEqual(state['turn_count_since_last_review'], 9)
        self.assertTrue(state['pending_review'])
        self.assertIsNone(state['last_message_at'])
        self.assertNotIn('Synthetic arbitrary state text', output)
