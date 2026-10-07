# ABOUTME: Exercises native MCP permission hooks with current user and managed rules.
# ABOUTME: Confirms policy changes and malformed managed sources cannot inherit a prior grant.
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lifeos_hook_bridge import bridge as module


SAFETY = os.environ.get('LIFEOS_PERMISSION_HOOK')
TOOL = 'mcp__permission__ping'


@unittest.skipUnless(SAFETY, 'Prepared native Safety is required')
class McpRuleBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='mcp-rules-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.root = self.home / '.claude'
        self.root.mkdir()
        self.settings = self.root / 'settings.json'
        self.settings.write_text(json.dumps({'hooks': {'PermissionRequest': [
            {'matcher': 'mcp__.*', 'hooks': [{'type': 'command', 'command': 'bun ' + str(SAFETY)}]}]}}))
        self.bridge = module.HookBridge(self.settings, self.root, lifeos_home=self.home)
        self.addCleanup(self.bridge.close)

    def rules(self, permissions):
        value = json.loads(self.settings.read_text())
        value['permissions'] = permissions
        self.settings.write_text(json.dumps(value))

    def test_ask_rule_preserves_review_despite_a_native_allow(self):
        self.rules({'ask': [TOOL]})
        self.assertEqual(self.bridge.pre_tool_call(TOOL, {}, session_id='ask')['action'], 'approve')
        log = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/permission-decisions.jsonl'
        self.assertEqual(json.loads(log.read_text().splitlines()[-1])['decision'], 'allow')

    def test_denial_stops_the_hook_and_prior_allow_before_execution(self):
        self.rules({'allow': [TOOL], 'deny': ['mcp__permission']})
        self.assertEqual(self.bridge.pre_tool_call(TOOL, {}, session_id='deny')['action'], 'block')
        self.assertFalse((self.root / 'LIFEOS/MEMORY/OBSERVABILITY/permission-decisions.jsonl').exists())

    def test_policy_change_replaces_a_prior_grant_on_the_next_call(self):
        self.rules({'allow': [TOOL]})
        self.assertIsNone(self.bridge.pre_tool_call(TOOL, {}, session_id='change'))
        self.rules({'deny': [TOOL]})
        self.assertEqual(self.bridge.pre_tool_call(TOOL, {}, session_id='change')['action'], 'block')

    def test_managed_deny_overrides_user_allow(self):
        policy = self.home / 'policy'
        policy.mkdir()
        (policy / 'managed-settings.json').write_text(json.dumps({'permissions': {'deny': [TOOL]}}))
        self.rules({'allow': [TOOL]})
        with patch.object(module, 'POLICY_DIRECTORY', policy):
            self.assertEqual(self.bridge.pre_tool_call(TOOL, {}, session_id='managed')['action'], 'block')

    def test_managed_only_ignores_user_allow(self):
        policy = self.home / 'policy'
        policy.mkdir()
        (policy / 'managed-settings.json').write_text(json.dumps({'allowManagedPermissionRulesOnly': True,
                                                               'permissions': {'ask': [TOOL]}}))
        self.rules({'allow': [TOOL]})
        with patch.object(module, 'POLICY_DIRECTORY', policy):
            self.assertEqual(self.bridge.pre_tool_call(TOOL, {}, session_id='managed-only')['action'], 'approve')

    def test_malformed_managed_policy_stays_reviewed_after_native_allow(self):
        policy = self.home / 'policy'
        policy.mkdir()
        (policy / 'managed-settings.json').write_text('{')
        self.rules({'allow': [TOOL]})
        with patch.object(module, 'POLICY_DIRECTORY', policy), self.assertLogs(module.LOG, level='WARNING') as logs:
            self.assertEqual(self.bridge.pre_tool_call(TOOL, {}, session_id='invalid')['action'], 'approve')
        self.assertTrue(any('managed permission policy' in line for line in logs.output))
