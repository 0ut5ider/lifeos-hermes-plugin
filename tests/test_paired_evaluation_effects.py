# ABOUTME: Rejects evaluation evidence without a completed real runner result.
# ABOUTME: Checks sentinel changes, debounce state, model execution, and failure publication.
import copy
import unittest
import tempfile
import sys
from pathlib import Path

from scripts.paired_evaluation_effects import (EVALUATION_CASES, expected_evaluation, check_evaluation,
                                             seed_evaluation, configure_evaluation)
from scripts.paired_lifecycle_effects import check_pair


class PairedEvaluationTests(unittest.TestCase):
    def test_child_route_uses_the_installed_plugin_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shim = root / 'plugins/lifeos-hook-bridge/bin/claude'
            shim.parent.mkdir(parents=True)
            shim.write_text('Installed inference entry point\n')
            environment = {'PATH': '/usr/bin'}
            configure_evaluation(root / 'home', 'hermes', {'plugins_path': str(root / 'plugins'), 'command': [sys.executable]},
                                 'http://127.0.0.1:1234', environment)
            self.assertTrue((root / 'home/.local/bin/claude').is_file())
            self.assertIn('-m hermes_cli.main', (root / 'home/.local/bin/hermes').read_text())

    def test_suite_preparation_creates_the_real_runner_link(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            source = Path(directory) / 'source'
            (source / 'LIFEOS/TOOLS').mkdir(parents=True)
            seed_evaluation(home, source, 'evaluation-write-pass')
            self.assertEqual((home / '.claude/LIFEOS/TOOLS').resolve(), source / 'LIFEOS/TOOLS')
            self.assertTrue((home / '.claude/LIFEOS/USER/CUSTOMIZATIONS/SKILLS/Evals/Suites/paired-config-fixture.yaml').is_file())

    def test_real_runner_and_tool_turn_requests_are_both_accepted(self):
        before, after = expected_evaluation('evaluation-write-pass')
        side = {'before': before, 'after': after, 'event': 'PostToolUse', 'hook_exit_codes': [0],
                'cli_exit_code': 0, 'model_generation_requests': 3, 'model_successful_responses': 3}
        self.assertEqual(check_pair({'id': 'evaluation-write-pass', 'native': side,
                                    'hermes': copy.deepcopy(side)}), [])

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
