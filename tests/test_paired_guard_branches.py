# ABOUTME: Rejects guard evidence that permits blocked execution or loses target state.
# ABOUTME: Checks real-client assertions for the remaining nested Bash guard branches.
import copy
import unittest

from scripts.paired_lifecycle_effects import GUARD_BRANCHES, guard_expectation, check_pair


class PairedGuardBranchTests(unittest.TestCase):
    def case(self, name):
        before, after = guard_expectation(name)
        blocked = GUARD_BRANCHES[name]['blocked']
        side = {'before': before, 'after': after, 'hook_exit_codes': [2 if blocked else 0],
                'event': 'PreToolUse', 'cli_exit_code': 0, 'model_generation_requests': 2,
                'model_successful_responses': 2}
        return {'id': name, 'native': side, 'hermes': copy.deepcopy(side)}

    def test_each_branch_requires_its_measured_decision_and_target_effect(self):
        for name in GUARD_BRANCHES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])
                for field in ('command_matches', 'user_response_delivered'):
                    altered = self.case(name)
                    for side in ('native', 'hermes'):
                        altered[side]['after'][field] = False
                    self.assertTrue(check_pair(altered))

    def test_denials_require_no_execution_and_model_delivery(self):
        for name, definition in GUARD_BRANCHES.items():
            if not definition['blocked']:
                continue
            for field, value in (('model_received_block', False), ('tool_output_in_model', True),
                                 ('block_message_emitted', False), ('target_content_matches', False)):
                with self.subTest(name=name, field=field):
                    altered = self.case(name)
                    for side in ('native', 'hermes'):
                        altered[side]['after'][field] = value
                    self.assertTrue(check_pair(altered))

    def test_allowance_requires_execution_and_the_expected_target_content(self):
        for name, definition in GUARD_BRANCHES.items():
            if definition['blocked']:
                continue
            for field in ('tool_output_in_model', 'target_content_matches'):
                with self.subTest(name=name, field=field):
                    altered = self.case(name)
                    for side in ('native', 'hermes'):
                        altered[side]['after'][field] = False
                    self.assertTrue(check_pair(altered))
