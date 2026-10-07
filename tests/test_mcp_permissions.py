# ABOUTME: Checks MCP permission scope and denial precedence across settings sources.
# ABOUTME: Keeps server boundaries, policy changes, and malformed policy from granting execution.
import unittest

from lifeos_hook_bridge.mcp_permissions import permission_decision


class McpPermissionTests(unittest.TestCase):
    def test_exact_tool_and_server_rules_have_distinct_scope(self):
        for rule in ('mcp__lab', 'mcp__lab__*', 'mcp__lab__read'):
            with self.subTest(rule=rule):
                self.assertEqual(permission_decision('mcp__lab__read', [{'deny': [rule]}]), 'deny')
                self.assertEqual(permission_decision('mcp__laboratory__read', [{'deny': [rule]}]), 'none')
        self.assertEqual(permission_decision('mcp__lab__write', [{'deny': ['mcp__lab__read']}]), 'none')

    def test_tool_glob_is_anchored_to_the_literal_server(self):
        rules = [{'allow': ['mcp__lab__get_*']}]
        self.assertEqual(permission_decision('mcp__lab__get_note', rules), 'allow')
        self.assertEqual(permission_decision('mcp__other__get_note', rules), 'none')
        self.assertEqual(permission_decision('mcp__lab__write_note', rules), 'none')

    def test_deny_and_ask_take_precedence_over_any_allow_source(self):
        tool = 'mcp__lab__read'
        self.assertEqual(permission_decision(tool, [{'allow': [tool]}, {'deny': ['mcp__lab']}]), 'deny')
        self.assertEqual(permission_decision(tool, [{'allow': [tool]}, {'ask': ['mcp__lab']}]), 'ask')
        self.assertEqual(permission_decision(tool, [{'ask': [tool]}, {'deny': [tool]}]), 'deny')

    def test_malformed_sources_require_review_despite_an_allow(self):
        tool = 'mcp__lab__read'
        for broken in (None, {'deny': 'mcp__lab'}, {'ask': [None]}):
            with self.subTest(broken=broken):
                self.assertEqual(permission_decision(tool, [{'allow': [tool]}, broken]), 'unknown')
        self.assertEqual(permission_decision(tool, [None, {'deny': [tool]}]), 'deny')

    def test_settings_parameter_rules_do_not_grant_mcp_execution(self):
        self.assertEqual(permission_decision('mcp__lab__read', [{'allow': ['mcp__lab__read(path:note)']}]), 'none')

    def test_unrelated_rules_do_not_change_mcp_policy(self):
        self.assertEqual(permission_decision('mcp__lab__read', [{'deny': ['Bash', 'Edit(.env)']}]), 'none')

    def test_broad_deny_and_ask_globs_cannot_be_bypassed(self):
        tool = 'mcp__lab__read'
        for rule in ('*', 'mcp__*', 'mcp__lab__*'):
            with self.subTest(rule=rule):
                self.assertEqual(permission_decision(tool, [{'deny': [rule], 'allow': [tool]}]), 'deny')
                self.assertEqual(permission_decision(tool, [{'ask': [rule], 'allow': [tool]}]), 'ask')
