# ABOUTME: Rejects evaluation evidence without a completed real runner result.
# ABOUTME: Checks sentinel changes, debounce state, model execution, and failure publication.
import copy
import unittest

from scripts.paired_evaluation_effects import EVALUATION_CASES, expected_evaluation, check_evaluation


class PairedEvaluationTests(unittest.TestCase):
    def test_all_required_runner_outcomes_are_measured(self):
        for case in EVALUATION_CASES:
            before, after = expected_evaluation(case)
            with self.subTest(case=case):
                self.assertEqual(check_evaluation(case, before, after), [])
                for field in ('target_matches', 'input_matches', 'runner_lock_absent'):
                    invalid = copy.deepcopy(after)
                    invalid[field] = False
                    self.assertTrue(check_evaluation(case, before, invalid))

    def test_completed_evaluations_require_actual_trial_output(self):
        for case in ('evaluation-write-pass', 'evaluation-edit-pass', 'evaluation-write-fail'):
            before, after = expected_evaluation(case)
            for field in ('trial_output_matches', 'published_result_matches'):
                invalid = copy.deepcopy(after)
                invalid[field] = False
                self.assertTrue(check_evaluation(case, before, invalid))
