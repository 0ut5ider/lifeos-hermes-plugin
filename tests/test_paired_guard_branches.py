# ABOUTME: Rejects guard evidence that permits blocked execution or loses target state.
# ABOUTME: Checks real-client assertions for the remaining nested Bash guard branches.
import copy
import unittest
import json
import tempfile
from pathlib import Path

from scripts.paired_lifecycle_effects import GUARD_BRANCHES, guard_expectation, check_pair, make_fixture


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

    def test_real_branch_fixture_admits_bash_while_retaining_the_native_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            (source / 'hooks').mkdir(parents=True)
            (source / 'hooks/PreToolGuard.hook.ts').write_text('Source identity\n')
            home = root / 'home'
            make_fixture(home, 'guard-bash-gmail-routed', source, root / 'trace.py')
            settings = json.loads((home / '.claude/settings.json').read_text())
            self.assertEqual(settings.get('permissions'), {'allow': ['Bash']})
            self.assertEqual(settings['hooks']['PreToolUse'][0]['matcher'], 'Bash|Write|Edit|MultiEdit')
            self.assertEqual((home / 'project/gmail.ts').read_text().splitlines()[-1],
                             'console.log("PAIR_GUARD_OUTPUT");')
