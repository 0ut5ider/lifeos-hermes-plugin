# ABOUTME: Drives a complete Hermes model and native memory tool turn over local HTTP.
# ABOUTME: Verifies committed receipt propagation and preserved disabled built-in memory files.
import json
from pathlib import Path
import sys
import unittest

from test_memory_native import OWNER
import test_memory_host as host_fixture


class MemoryAgentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = host_fixture.MemoryHostTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_actual_agent_turn_commits_native_fact_and_reports_its_receipt(self):
        marker = 'Synthetic complete agent memory marker'
        def respond(request):
            tools = [message for message in request['messages'] if message.get('role')=='tool']
            if not tools:
                return {'role':'assistant','content':None,'tool_calls':[{'id':'synthetic-save','type':'function',
                    'function':{'name':'lifeos_memory_remember','arguments':json.dumps({'category':'project','content':marker,
                      'title':'Synthetic agent fact','project':'lab','request_id':'agent-save'})}}]}
            receipt = json.loads(tools[-1]['content'])
            return {'role':'assistant','content':json.dumps({'status':receipt['status'],'reference':receipt['reference'],
                                                           'writer':receipt['writer']})}
        self.fixture.fixture.response_message = respond
        result = self.fixture.initialize({'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False},
                                         operation='conversation',message='Remember a synthetic lab fact and report its saved reference.')
        turn = result['conversation']
        self.assertFalse(turn.get('failed'),turn)
        self.assertEqual(result['diagnostics'],'')
        receipt = json.loads(turn['final_response'])
        self.assertEqual(receipt['status'],'committed')
        self.assertEqual(receipt['writer'],'chat-a:100')
        native = self.fixture.fixture.fixture.fixture.memory.get(OWNER,receipt['reference'])
        self.assertEqual(native['content'],marker)
        self.assertEqual(native['source'], {'kind': 'explicit', 'session': 'session'})
        calls = [request for request in self.fixture.fixture.received if request['path']=='/v1/chat/completions']
        self.assertEqual(len(calls),2)
        self.assertTrue(any(message.get('role')=='tool' for message in calls[-1]['body']['messages']))
        for request in calls:
            for data in self.fixture.original.values():
                self.assertNotIn(data.decode().strip(),json.dumps(request['body']))
        self.outcome = result

    def test_actual_agent_turn_rejects_unknown_author_before_model_or_memory_calls(self):
        result = self.fixture.initialize({'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False},
                                         operation='conversation',author='unknown',message='Remember a synthetic denied fact.')
        turn = result['conversation']
        self.assertEqual(turn['turn_exit_reason'],'prompt_blocked')
        self.assertEqual(turn['api_calls'],0)
        self.assertIn('no approved identity binding',turn['final_response'])
        self.assertFalse(any(request['path']=='/v1/chat/completions' for request in self.fixture.fixture.received))
        self.assertEqual(self.fixture.fixture.fixture.fixture.memory.recall(OWNER,'synthetic denied fact'),[])
        self.outcome = result

    def change_fact(self, operation, *, native_recall=False):
        marker = 'Synthetic superseded agent conversation claim'
        replacement = 'Synthetic corrected agent conversation claim'
        native = self.fixture.fixture.fixture.fixture
        prefix = 'RULE: ' if native_recall else ''
        saved = native.remember(prefix+marker, 'conversation-original','principal' if native_recall else 'project')
        if native_recall:
            connector = native.root/'LIFEOS/USER/CONFIG/memory-access.json'
            connector.parent.mkdir()
            connector.write_text(json.dumps({'version':1,'command':[sys.executable,
                str(Path(__file__).parents[1]/'lifeos_hook_bridge/memory_rpc.py'),
                '--configuration',str(self.fixture.fixture.fixture.path)]}))
            connector.chmod(0o600)
            (native.root/'settings.json').write_text(json.dumps({'hooks':{'UserPromptSubmit':[{'hooks':[
                {'type':'command','command':'bun --no-install '+str(native.root/'hooks/LoadMemory.hook.ts')}]}]}}))
        def respond(request):
            results = [message for message in request['messages'] if message.get('role')=='tool']
            if not results:
                name = 'lifeos_memory_get'
                arguments = {'reference':saved['reference']}
                content = None
            elif len(results) == 1:
                name = 'lifeos_memory_'+operation
                arguments = {'reference':saved['reference'],'request_id':'conversation-'+operation}
                if operation == 'correct':
                    arguments['content'] = prefix+replacement
                content = marker
            else:
                receipt = json.loads(results[-1]['content'])
                return {'role':'assistant','content':json.dumps({'status':receipt['status'],'reference':receipt['reference']})}
            return {'role':'assistant','content':content,'tool_calls':[{'id':'synthetic-'+name,'type':'function',
                    'function':{'name':name,'arguments':json.dumps(arguments)}}]}
        self.fixture.fixture.response_message = respond
        result = self.fixture.initialize({'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False},
                                         operation='conversation',message=operation.title()+' the referenced synthetic lab fact.')
        turn = result['conversation']
        self.assertFalse(turn.get('failed'),turn)
        self.assertEqual(result['diagnostics'],'')
        receipt = json.loads(turn['final_response'])
        self.assertEqual(receipt['status'],'committed')
        calls = [request for request in self.fixture.fixture.received if request['path']=='/v1/chat/completions']
        self.assertEqual(len(calls),3)
        self.assertIn(marker,json.dumps(calls[1]['body']))
        self.assertNotIn(marker,json.dumps(calls[2]['body']))
        self.assertIn(marker,json.dumps(turn['messages']))
        current = native.memory.recall(OWNER,'agent conversation claim')
        self.assertEqual([row['content'] for row in current],[prefix+replacement] if operation == 'correct' else [])
        if native_recall:
            self.assertIn('<lifeos-memory>',json.dumps(calls[0]['body']))
            self.assertIn(marker,json.dumps(calls[0]['body']))
        self.outcome = result

    def test_actual_correction_turn_refreshes_model_history_and_preserves_transcript(self):
        self.change_fact('correct')

    def test_actual_forget_turn_refreshes_model_history_and_preserves_transcript(self):
        self.change_fact('forget')

    def test_actual_native_recall_correction_turn_removes_cached_hook_context(self):
        self.change_fact('correct',native_recall=True)

    def test_actual_native_recall_forget_turn_removes_cached_hook_context(self):
        self.change_fact('forget',native_recall=True)


if __name__ == '__main__':
    unittest.main()
