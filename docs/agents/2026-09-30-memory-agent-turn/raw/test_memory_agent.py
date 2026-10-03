# ABOUTME: Drives a complete Hermes model and native memory tool turn over local HTTP.
# ABOUTME: Verifies committed receipt propagation and preserved disabled built-in memory files.
import json
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
        receipt = json.loads(turn['final_response'])
        self.assertEqual(receipt['status'],'committed')
        self.assertEqual(receipt['writer'],'chat-a:100')
        native = self.fixture.fixture.fixture.fixture.memory.get(OWNER,receipt['reference'])
        self.assertEqual(native['content'],marker)
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


if __name__ == '__main__':
    unittest.main()
