# ABOUTME: Checks governed native PULSE snapshots against real isolated source files.
# ABOUTME: Preserves owner diagnostics while excluding retired text and redirected sources.
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from lifeos_hook_bridge.memory_preferences import MemoryPreferences
import test_memory_cortex_health as health_fixture
from test_memory_native import SOURCE, OWNER


class MemoryPulseTests(unittest.TestCase):
    def setUp(self):
        self.fixture = health_fixture.MemoryCortexHealthTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.obs = self.fixture.root, self.fixture.obs
        (self.root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
        self.preferences = MemoryPreferences(self.fixture.fixture.configuration.path, self.root,
            self.fixture.fixture.fixture.home / '.ssh/authorized_keys', Path('/usr/bin/python3'),
            Path(__file__).parents[1] / 'lifeos_hook_bridge/memory_mcp.py')

    def snapshot(self, view='snapshot'):
        return self.preferences.pulse_snapshot(view)

    def test_owner_snapshot_preserves_current_hot_facts_and_native_defaults(self):
        self.fixture.fixture.fixture.remember('RULE: Synthetic current PULSE fact', 'pulse-current', 'principal')
        snapshot = self.snapshot()
        self.assertEqual(snapshot['principalMemory']['entries'], ['RULE: Synthetic current PULSE fact'])
        self.assertEqual(snapshot['principalMemory']['count'], 1)
        self.assertEqual(snapshot['daMemory']['count'], 0)
        self.assertEqual(snapshot['cadenceConfig']['turn_threshold'], 8)
        self.assertEqual(snapshot['derivedState'], 'cold')
        self.assertEqual(snapshot['pendingProposals'], 0)

    def test_committed_correction_keeps_current_fact_but_filters_retained_copy(self):
        native = self.fixture.fixture.fixture
        claim = 'RULE: Synthetic PULSE baseline setting'
        saved = native.remember(claim, 'pulse-original', 'principal')
        corrected = native.memory.correct(OWNER, saved['reference'], claim + ' now revised', 'pulse-correction')
        current = native.memory.get(OWNER, corrected['reference'])['content']
        (self.obs / 'review-state.json').write_text(json.dumps({'retained': current}))
        snapshot = self.snapshot()
        self.assertEqual(snapshot['principalMemory']['entries'], [current])
        self.assertNotIn(claim, snapshot['reviewState']['retained'])

    def test_current_unicode_fact_keeps_native_utf16_character_count(self):
        claim = 'RULE: Synthetic PULSE unicode fact 🧠'
        self.fixture.fixture.fixture.remember(claim, 'pulse-unicode', 'principal')
        hot = self.snapshot()['principalMemory']
        self.assertEqual(hot['entries'], [claim])
        self.assertEqual(hot['charsUsed'], len(claim.encode('utf-16-le')) // 2)

    def test_retired_dynamic_keys_are_omitted_without_changing_fixed_counts(self):
        native = self.fixture.fixture.fixture
        marker = 'SyntheticPulseRetiredKey'
        saved = native.remember('RULE: ' + marker, 'pulse-key', 'principal')
        native.memory.forget(OWNER, saved['reference'], 'forget-pulse-key')
        directory = self.obs / 'reviewer-runs/2026-10-01T00-00-00-000Z'
        directory.mkdir(parents=True)
        (directory / 'dispatch.log').write_text('Items: 2 (succeeded=1 failed=1)\nBy type: '
                                               + json.dumps({marker: 1, 'memory': 1}) + '\n')
        (self.obs / 'review-state.json').write_text(json.dumps({'turn_count_since_last_review': 2,
            'nested': {marker: 'value', 'current': 'control'}, 'encoded': json.dumps({marker: 1})}))
        for view in ('state', 'runs', 'snapshot'):
            with self.subTest(view=view):
                result = self.snapshot(view)
                self.assertNotIn(marker, json.dumps(result))
                state = result.get('reviewState', result) if isinstance(result, dict) else None
                if state is not None:
                    self.assertEqual(state['nested'], {'current': 'control'})
                    self.assertEqual(state['turn_count_since_last_review'], 2)
                if view != 'state':
                    run = result['recentRuns'][0] if view == 'snapshot' else result[0]
                    self.assertEqual(run['byType'], {'memory': 1})
                    self.assertEqual(run['itemsTotal'], 2)

    def test_retiring_operational_field_word_keeps_declared_field_only(self):
        native = self.fixture.fixture.fixture
        saved = native.remember('RULE: pending_review', 'pulse-field', 'principal')
        native.memory.forget(OWNER, saved['reference'], 'forget-pulse-field')
        (self.obs / 'review-state.json').write_text(json.dumps({'pending_review': True,
            'nested': {'pending_review': 'Synthetic historical text'}}))
        state = self.snapshot('state')
        self.assertTrue(state['pending_review'])
        self.assertEqual(state['nested'], {})

    def test_proposal_status_schema_cannot_authorize_nested_state_field(self):
        native = self.fixture.fixture.fixture
        saved = native.remember('RULE: status', 'pulse-status', 'principal')
        native.memory.forget(OWNER, saved['reference'], 'forget-pulse-status')
        (self.obs / 'review-state.json').write_text(json.dumps({'pending_review': True,
            'reviewer': {'status': 1}, 'nested': {'status': 2}}))
        (self.obs / 'pending-proposals.jsonl').write_text(json.dumps({'id': 'synthetic-status-proposal',
            'status': 'pending', 'edit': 'Synthetic current proposal',
            'ts': datetime.now(timezone.utc).isoformat()}) + '\n')
        result = self.snapshot()
        self.assertEqual(result['proposalsRecent'][0]['status'], 'pending')
        self.assertEqual(result['pendingProposals'], 1)
        self.assertEqual(result['reviewState']['reviewer'], {})
        self.assertEqual(self.snapshot('state')['reviewer'], {})

    def test_owner_snapshot_keeps_health_decision_without_retired_error(self):
        marker = 'Synthetic retired PULSE health marker'
        saved = self.fixture.fixture.fixture.remember('RULE: ' + marker, 'pulse-retired', 'principal')
        self.fixture.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-pulse')
        (self.obs / 'memory-health.jsonl').write_text(json.dumps({'ts': datetime.now(timezone.utc).isoformat(),
            'overall': 'critical', 'counts': {'critical': 2, 'warn': 1, 'ok': 3},
            'findings': [{'severity': 'critical', 'message': marker}]}) + '\n')
        snapshot = self.snapshot()
        self.assertEqual(snapshot['derivedState'], 'unhealthy_critical')
        self.assertEqual(snapshot['health']['overall'], 'critical')
        self.assertEqual(snapshot['health']['counts']['critical'], 2)
        self.assertNotIn(marker, json.dumps(snapshot))

    def test_retired_proposal_does_not_remove_native_queue_counts(self):
        marker = 'Synthetic retired PULSE proposal'
        saved = self.fixture.fixture.fixture.remember('RULE: ' + marker, 'pulse-proposal', 'principal')
        self.fixture.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-pulse-proposal')
        (self.obs / 'pending-proposals.jsonl').write_text(json.dumps({'id': 'synthetic-pulse-proposal',
            'status': 'pending', 'edit': marker, 'ts': datetime.now(timezone.utc).isoformat()}) + '\n')
        snapshot = self.snapshot()
        self.assertEqual(snapshot['pendingProposals'], 1)
        self.assertNotIn(marker, json.dumps(snapshot))

    def test_all_four_views_keep_native_missing_field_contracts(self):
        self.assertEqual(self.snapshot('state'), {})
        self.assertIsNone(self.snapshot('health'))
        self.assertEqual(self.snapshot('runs'), [])
        snapshot = self.snapshot()
        self.assertIn('reviewState', snapshot)
        self.assertEqual(snapshot['recentRuns'], [])

    def test_configuration_binding_is_rechecked_for_each_snapshot(self):
        self.snapshot()
        self.fixture.fixture.configuration.update(lambda value: value.update(root=str(self.root.parent / 'other')))
        with self.assertRaises(RuntimeError):
            self.snapshot()

    def test_unknown_view_cannot_become_an_arbitrary_file_read(self):
        for view in ('../CONFIG', 'graph', '/api/memory', '', {}, []):
            with self.subTest(view=view), self.assertRaises(ValueError):
                self.snapshot(view)

    def test_redirected_hot_file_cannot_become_private_configuration(self):
        path = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        path.unlink()
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-pulse-secret.md'
        secret.write_text('<!-- BEGIN ENTRIES -->\nRULE: Synthetic private configuration\n<!-- END ENTRIES -->\n')
        path.symlink_to(secret)
        with self.assertRaises(RuntimeError):
            self.snapshot()

    def test_dispatch_redirect_is_refused_before_native_run_enumeration(self):
        directory = self.obs / 'reviewer-runs/2026-10-01T00-00-00-000Z'
        directory.mkdir(parents=True)
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-pulse-dispatch.log'
        secret.write_text('Items: 1 (succeeded=1 failed=0)\n[0] OK memory: synthetic-config-marker.md\n')
        (directory / 'dispatch.log').symlink_to(secret)
        with self.assertRaises(RuntimeError):
            self.snapshot()

    def test_cadence_returns_supported_settings_without_extra_configuration_text(self):
        config = self.root / 'LIFEOS/USER/CONFIG/memory-review.json'
        config.write_text(json.dumps({'turn_threshold': 12, 'min_minutes_between': 42, 'idle_threshold': 3,
            'confidence_threshold': 0.8, 'secret': 'Synthetic unsupported cadence value'}))
        snapshot = self.snapshot()
        self.assertEqual(snapshot['cadenceConfig']['turn_threshold'], 12)
        self.assertNotIn('Synthetic unsupported cadence value', json.dumps(snapshot))

    def test_native_runs_keep_dispatch_counts_and_current_item_labels(self):
        directory = self.obs / 'reviewer-runs/2026-10-01T00-00-00-000Z'
        directory.mkdir(parents=True)
        (directory / 'dispatch.log').write_text('Items: 2 (succeeded=1 failed=1)\nBy type: {"memory":2}\n'
                                              '[0] OK memory: /synthetic/current-pulse-item.md\n')
        run = self.snapshot('runs')[0]
        self.assertEqual(run['itemsTotal'], 2)
        self.assertEqual(run['itemsOk'], 1)
        self.assertEqual(run['itemsFailed'], 1)
        self.assertEqual(run['byType'], {'memory': 2})
        self.assertEqual(run['itemPaths'][0]['file'], 'current-pulse-item.md')
