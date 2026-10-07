# ABOUTME: Rejects matching functional evidence that omits required hook effects.
# ABOUTME: Prevents direct native handler comparisons from claiming native CLI dispatch.

import copy
import json
from pathlib import Path
import unittest

from scripts.hook_completion_assertions import check_control


ROOT = Path(__file__).resolve().parents[1] / 'docs/verification/2026-10-06-hook-completion'


class HookCompletionAssertionTests(unittest.TestCase):
    def records(self, filename):
        return json.loads((ROOT / filename).read_text())['cases']

    def test_retained_controls_pass(self):
        for filename in ('config-control.json', 'web-results.json', 'batch-results.json'):
            for record in self.records(filename):
                with self.subTest(case=record['id']):
                    self.assertEqual(check_control(record), [])

    def test_web_evidence_requires_real_model_delivery(self):
        for record in self.records('web-results.json'):
            altered = copy.deepcopy(record)
            altered['hermes_record']['after']['context_in_model'] = [False]
            self.assertTrue(check_control(altered))
            altered = copy.deepcopy(record)
            altered['native_cli_dispatch'] = True
            self.assertIn('functional control dispatch scope is invalid', check_control(altered))

    def test_partial_patch_cannot_claim_a_checkpoint(self):
        record = next(r for r in self.records('batch-results.json') if r['id'] == 'batch-partial')
        for side in ('native', 'hermes'):
            record[side]['checkpoint_records_criterion'] = True
        self.assertTrue(check_control(record))

    def test_configuration_evidence_requires_the_changed_file(self):
        record = self.records('config-control.json')[0]
        for side in ('native', 'hermes'):
            record[side]['changes'][2]['native_audit_path'] = 'settings.json'
        self.assertTrue(check_control(record))

    def test_real_evaluation_operations_require_every_measured_effect(self):
        path = ROOT.parent / '2026-10-06-step1/evaluation-operations/operation-results.json'
        for record in json.loads(path.read_text())['cases']:
            self.assertEqual(check_control(record), [])
            for field in ('hook_errors_absent', 'single_completed_run', 'runner_lock_absent',
                          'valid_fire_state', 'passed', 'trial_output_matches', 'published_result_matches'):
                changed = copy.deepcopy(record)
                for side in ('native', 'hermes'):
                    changed[side][field] = False
                self.assertTrue(check_control(changed), field)
            changed = copy.deepcopy(record)
            changed['native_cli_dispatch'] = True
            self.assertTrue(check_control(changed))
