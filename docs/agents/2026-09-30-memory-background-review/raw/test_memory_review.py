# ABOUTME: Exercises real Hermes background skill review with LifeOS lasting memory.
# ABOUTME: Verifies native skill writes, staged approval, and generated memory exclusions.
import json
import unittest

import test_memory_host as host_fixture
from test_memory_native import OWNER


OWNERSHIP = {'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False}
SKILL = '''---
name: synthetic-review
description: Verify a synthetic local task.
---

# Verify a task

1. Read the task requirements.
2. Run the task verification command.
3. Report the observed result.
'''


class MemoryReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = host_fixture.MemoryHostTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def run_review(self, *, approval=False, focus=None, message='Verify a synthetic task.',explicit=False):
        def respond(request):
            reviewing = any(item.get('role')=='user' and isinstance(item.get('content'),str)
                            and item['content'].startswith('Review the conversation above')
                            for item in request['messages'])
            if not reviewing:
                return {'role':'assistant','content':'SYNTHETIC-FOREGROUND-OK'}
            receipts = [item for item in request['messages'] if item.get('role')=='tool']
            if receipts:
                return {'role':'assistant','content':receipts[-1]['content']}
            return {'role':'assistant','content':None,'tool_calls':[{'id':'synthetic-review-write','type':'function',
                    'function':{'name':'skill_manage','arguments':json.dumps({'operations':[
                        {'action':'create','name':'synthetic-review','content':SKILL}]})}}]}
        self.fixture.fixture.response_message = respond
        result = self.fixture.initialize(OWNERSHIP,operation='conversation',message=message,
                                         background_review=True,review_focus=focus,skill_approval=approval,
                                         review_explicit=explicit)
        self.assertTrue(result['review_done'],result)
        self.assertFalse(result['conversation'].get('failed'),result['conversation'])
        self.calls = [row['body'] for row in self.fixture.fixture.received if row['path']=='/v1/chat/completions']
        self.outcome = result
        return result

    def test_background_review_creates_skill_without_reenabling_builtin_memory(self):
        self.run_review()
        self.assertEqual(len(self.calls),3)
        self.assertEqual((self.fixture.home/'skills/synthetic-review/SKILL.md').read_text(),SKILL)
        self.assertEqual(list((self.fixture.home/'pending/skills').glob('*.json')),[])
        for request in self.calls:
            for marker in self.fixture.original.values():
                self.assertNotIn(marker.decode().strip(),json.dumps(request))
        self.assertTrue(self.outcome['review_summaries'])

    def test_background_review_preserves_skill_approval_and_stages_write(self):
        self.run_review(approval=True,focus='Synthetic skill review',explicit=True)
        self.assertEqual(len(self.calls),3)
        self.assertFalse((self.fixture.home/'skills/synthetic-review/SKILL.md').exists())
        staged = list((self.fixture.home/'pending/skills').glob('*.json'))
        self.assertEqual(len(staged),1)
        record = json.loads(staged[0].read_text())
        self.assertEqual(record['origin'],'background_review')
        self.assertEqual(record['payload']['operations'][0]['content'],SKILL)
        self.assertIn('staged',self.calls[-1]['messages'][-1]['content'])

    def test_background_review_does_not_treat_generated_focus_as_a_human_quote(self):
        native = self.fixture.fixture.fixture.fixture
        marker = 'Synthetic forgotten review focus claim'
        saved = native.remember(marker,'review-focus')
        native.memory.forget(OWNER,saved['reference'],'review-focus-forget')
        self.run_review(focus=marker,explicit=True)
        self.assertEqual(len(self.calls),1)
        self.assertFalse((self.fixture.home/'skills/synthetic-review/SKILL.md').exists())

    def test_background_review_cannot_borrow_foreground_model_permission(self):
        self.fixture.fixture.host_config['auxiliary']['background_review'] = dict(
            self.fixture.fixture.route,model='synthetic-unapproved-review-model',api_key='synthetic-key')
        self.run_review()
        self.assertEqual(len(self.calls),1)
        self.assertFalse((self.fixture.home/'skills/synthetic-review/SKILL.md').exists())

    def test_background_review_cannot_reuse_a_forgotten_foreground_quote(self):
        native = self.fixture.fixture.fixture.fixture
        marker = 'Synthetic forgotten review foreground claim'
        saved = native.remember(marker,'review-quote')
        native.memory.forget(OWNER,saved['reference'],'review-quote-forget')
        self.run_review(message=marker)
        self.assertEqual(len(self.calls),1)
        self.assertIn(marker,json.dumps(self.calls[0]))
        self.assertFalse((self.fixture.home/'skills/synthetic-review/SKILL.md').exists())


if __name__ == '__main__':
    unittest.main()
