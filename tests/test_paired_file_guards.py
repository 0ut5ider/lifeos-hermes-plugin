# ABOUTME: Requires real file-guard evidence to retain denied files and admitted changes.
# ABOUTME: Checks target content, native payloads, and model feedback for each file operation.
import copy
import unittest

from scripts.paired_lifecycle_effects import GUARD_FILE_BRANCHES, file_guard_expectation, check_pair


class PairedFileGuardTests(unittest.TestCase):
    def case(self, name):
        before, after = file_guard_expectation(name)
        blocked = GUARD_FILE_BRANCHES[name]['blocked']
        side = {'before': before, 'after': after, 'hook_exit_codes': [2 if blocked else 0],
                'event': 'PreToolUse', 'cli_exit_code': 0, 'model_generation_requests': 3,
                'model_successful_responses': 3}
        return {'id': name, 'native': side, 'hermes': copy.deepcopy(side)}

    def test_each_operation_requires_actual_target_and_content(self):
        for name in GUARD_FILE_BRANCHES:
            with self.subTest(name=name):
                self.assertEqual(check_pair(self.case(name)), [])
                for field in ('file_path_matches', 'input_content_matches', 'target_content_matches',
                              'user_response_delivered'):
                    altered = self.case(name)
                    for side in ('native', 'hermes'):
                        altered[side]['after'][field] = False
                    self.assertTrue(check_pair(altered))

    def test_denial_requires_exit_two_and_delivery_to_the_model(self):
        for name, definition in GUARD_FILE_BRANCHES.items():
            if not definition['blocked']:
                continue
            with self.subTest(name=name):
                altered = self.case(name)
                for side in ('native', 'hermes'):
                    altered[side]['hook_exit_codes'] = [0]
                    altered[side]['after']['model_received_block'] = False
                self.assertTrue(check_pair(altered))
