# ABOUTME: Verifies literal environment prefixes and nested wrappers retain command rule targets.
# ABOUTME: Characterizes existing wrapper and quoted-command behavior before extending environment parsing.
import unittest

from lifeos_hook_bridge.bash_permissions import bash_command_forms, bash_file_targets
from lifeos_hook_bridge.bridge import _bash_permission_rule_decision


class BashEnvironmentRuleTests(unittest.TestCase):
    def test_existing_wrapper_and_quoted_program_contract(self):
        for command, inner in [('timeout 10 cat target', 'cat target'),
                               ('command -- cat target', 'cat target'),
                               ('nice -n 2 cat target', 'cat target')]:
            self.assertIn(inner, bash_command_forms(command)[0][0])
        self.assertNotIn('touch target', bash_command_forms("sh -c 'touch target'")[0][0])
        self.assertEqual(bash_command_forms('command -v touch')[0], [('command -v touch',)])

    def test_environment_and_assignment_prefixes_cannot_hide_denied_command(self):
        for command in ['env PAIR=1 touch target', 'env -i PAIR=1 touch target',
                        'env -u PAIR touch target', 'env -- touch target',
                        "env PAIR='one two' touch target", 'PAIR=1 touch target',
                        'timeout 10 env PAIR=1 touch target',
                        'env PAIR=1 timeout 10 touch target']:
            with self.subTest(command=command):
                self.assertEqual(_bash_permission_rule_decision(command, [
                    {'allow': ['Bash(*)'], 'deny': ['Bash(touch target)']}]), 'deny')

    def test_wrapped_reader_keeps_actual_file_target(self):
        for command in ['env PAIR=1 cat target', 'PAIR=1 cat target',
                        'timeout 10 env PAIR=1 cat target']:
            with self.subTest(command=command):
                self.assertEqual(bash_file_targets(command), ([('read', 'target')], True))

    def test_unknown_env_options_do_not_grant_inner_allow(self):
        self.assertNotEqual(_bash_permission_rule_decision('env --unknown touch target', [
            {'allow': ['Bash(touch target)']}]), 'allow')
        self.assertEqual(bash_file_targets('env --unknown cat target'), ([], False))

    def test_environment_assignment_requires_review_for_inner_allow(self):
        self.assertNotEqual(_bash_permission_rule_decision('env PATH=/other touch target', [
            {'allow': ['Bash(touch target)']}]), 'allow')

    def test_assigned_directory_change_does_not_grant_an_unresolved_target(self):
        self.assertFalse(bash_file_targets('PAIR=1 cd sub && cat target')[1])
