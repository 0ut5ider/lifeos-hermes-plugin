# ABOUTME: Tests request-only history projection against native correction and forget state.
# ABOUTME: Verifies unchanged identity policy, protocol structure, and final admission checks.
from copy import deepcopy
import json
import sys
import threading
import unittest

from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_history import REMOVED
from lifeos_hook_bridge.memory_runtime import MemoryRuntime
import test_memory_runtime as runtime_fixture
from test_memory_native import OWNER


class MemoryHistoryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.marker = 'Synthetic removed projected conversation claim'
        self.saved = self.fixture.fixture.remember(self.marker,'projected-original')
        self.fixture.admit()

    def forget(self):
        self.fixture.fixture.memory.forget(OWNER,self.saved['reference'],'projected-forget')

    def project(self,request):
        sent = []
        def dispatch(projected):
            self.fixture.runtime.check_call(request=projected,**self.fixture.route,session_id='session')
            sent.append(projected)
        self.fixture.runtime.project_call(request=request,next_call=dispatch,
                                          **self.fixture.route,session_id='session')
        self.assertEqual(len(sent),1)
        return sent[0]

    def test_clean_projection_preserves_request_and_does_not_mutate_transcript(self):
        request = {'messages':[{'role':'system','content':'Synthetic constitution'},
                               {'role':'user','content':'Synthetic request'},
                               {'role':'assistant','content':self.marker}], 'model':'synthetic-model'}
        original = deepcopy(request)
        self.assertEqual(self.project(request),original)
        self.assertEqual(request,original)

    def test_generation_refresh_removes_retired_tool_and_assistant_content(self):
        request = {'messages':[{'role':'user','content':'Synthetic current request'},
            {'role':'assistant','content':self.marker,'tool_calls':[{'id':'tool-one','type':'function',
              'function':{'name':'lifeos_memory_remember','arguments':json.dumps({'content':self.marker.replace('removed ','removed\n'),'request_id':'stable-id'})}}]},
            {'role':'tool','tool_call_id':'tool-one','content':json.dumps({'content':self.marker,'reference':self.saved['reference']})}]}
        original = deepcopy(request)
        self.forget()
        result = self.project(request)
        self.assertEqual(request,original)
        self.assertNotIn(self.marker,json.dumps(result))
        assistant = result['messages'][1]
        self.assertEqual(assistant['content'],REMOVED)
        arguments = json.loads(assistant['tool_calls'][0]['function']['arguments'])
        self.assertEqual(arguments,{'content':REMOVED,'request_id':'stable-id'})
        self.assertEqual(result['messages'][2]['tool_call_id'],'tool-one')
        receipt = json.loads(result['messages'][2]['content'])
        self.assertEqual(receipt['reference'],self.saved['reference'])
        self.assertEqual(receipt['content'],REMOVED)
        with self.assertRaisesRegex(MemoryAdmissionError,'model history'):
            self.fixture.runtime.check_call(request=request,**self.fixture.route,session_id='session')

    def test_projection_replaces_previous_user_quote_but_keeps_current_explicit_quote(self):
        self.forget()
        result = self.project({'messages':[{'role':'user','content':self.marker},
                                           {'role':'assistant','content':'Synthetic response'},
                                           {'role':'user','content':self.marker}]})
        self.assertEqual(result['messages'][0]['content'],REMOVED)
        self.assertEqual(result['messages'][2]['content'],self.marker)

    def test_sdk_override_history_is_projected_without_overriding_other_fields(self):
        self.forget()
        request = {'messages':[{'role':'user','content':'Synthetic typed input'}],
                   'extra_body':{'messages':[{'role':'assistant','content':self.marker}], 'temperature':0.2}}
        original = deepcopy(request)
        result = self.project(request)
        self.assertEqual(result['messages'],result['extra_body']['messages'])
        self.assertEqual(result['extra_body']['temperature'],0.2)
        self.assertNotIn(self.marker,json.dumps(result))
        self.assertEqual(request,original)

    def test_projection_cannot_refresh_changed_policy_or_prompt(self):
        for changed in ('policy','prompt'):
            with self.subTest(changed=changed):
                self.setUp()
                self.forget()
                if changed == 'policy':
                    self.fixture.configuration['accounts']['chat-b:500'] = 'owner'
                    MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
                else:
                    (self.fixture.home/'SOUL.md').write_text('# Synthetic changed constitution\n')
                with self.assertRaisesRegex(MemoryAdmissionError,'invalidated memory context'):
                    self.project({'messages':[{'role':'user','content':'Synthetic new request'}]})

    def test_projection_cannot_change_authenticated_author_or_destination(self):
        self.forget()
        for metadata in (self.fixture.metadata(user='other'),self.fixture.metadata(destination='other')):
            with self.subTest(metadata=metadata),self.assertRaisesRegex(MemoryAdmissionError,'author or destination differs'):
                self.fixture.runtime.project_call(request={'messages':[{'role':'user','content':'Synthetic request'}]},
                    next_call=lambda _:self.fail('The denied request reached dispatch'),metadata=metadata,
                    **self.fixture.route,session_id='session')

    def test_protocol_identifiers_are_refused_instead_of_rewritten(self):
        self.forget()
        with self.assertRaisesRegex(MemoryAdmissionError,'model history'):
            self.project({'messages':[{'role':'assistant','content':None,'tool_calls':[{'id':self.marker,
                  'type':'function','function':{'name':'lifeos_memory_get','arguments':'{}'}}]}]})

    def test_projection_does_not_remove_required_system_instructions(self):
        self.forget()
        for role in ('system','developer'):
            with self.subTest(role=role),self.assertRaisesRegex(MemoryAdmissionError,'model system prompt'):
                self.project({'messages':[{'role':role,'content':self.marker}]})

    def test_uninspectable_history_is_refused_without_consuming_it(self):
        self.forget()
        messages = ({'role':'user','content':str(number)} for number in range(2))
        with self.assertRaisesRegex(MemoryAdmissionError,'materialized chat messages'):
            self.project({'messages':messages})
        self.assertEqual(len(list(messages)),2)

    def test_original_user_proof_excludes_appended_context_without_losing_the_user_quote(self):
        self.fixture.runtime.admit(self.fixture.metadata(),**self.fixture.route,is_first_turn=True,user_message=self.marker)
        self.forget()
        request = {'messages':[{'role':'user','content':self.marker+'\n\nSynthetic hook context: '+self.marker}]}
        result = self.project(request)
        self.assertEqual(result['messages'][0]['content'],self.marker+REMOVED)
        with self.assertRaisesRegex(MemoryAdmissionError,'model history'):
            self.fixture.runtime.check_call(request=request,**self.fixture.route,session_id='session')

    def test_original_multimodal_user_proof_excludes_appended_text_blocks(self):
        original = [{'type':'text','text':self.marker},{'type':'image_url','image_url':{'url':'https://example.invalid/synthetic.png'}}]
        self.fixture.runtime.admit(self.fixture.metadata(),**self.fixture.route,is_first_turn=True,user_message=original)
        self.forget()
        content = original+[{'type':'text','text':self.marker}]
        result = self.project({'messages':[{'role':'user','content':content}]})
        self.assertEqual(result['messages'][0]['content'][:2],original)
        self.assertEqual(result['messages'][0]['content'][2]['text'],REMOVED)

    def test_changed_current_user_input_cannot_borrow_an_original_input_proof(self):
        self.fixture.runtime.admit(self.fixture.metadata(),**self.fixture.route,is_first_turn=True,user_message='Synthetic admitted request')
        self.forget()
        with self.assertRaisesRegex(MemoryAdmissionError,'verify the current user input'):
            self.project({'messages':[{'role':'user','content':'Synthetic replacement request'}]})

    def test_each_admitted_turn_binds_its_current_input_without_changing_identity_policy(self):
        self.fixture.runtime.admit(self.fixture.metadata(),**self.fixture.route,is_first_turn=True,user_message='Synthetic first request')
        self.fixture.runtime.admit(self.fixture.metadata(),**self.fixture.route,is_first_turn=False,user_message='Synthetic second request')
        result = self.project({'messages':[{'role':'user','content':'Synthetic second request'}]})
        self.assertEqual(result['messages'][0]['content'],'Synthetic second request')

    def test_auxiliary_inputs_do_not_borrow_the_current_user_quote_exception(self):
        self.forget()
        self.fixture.runtime.admit(self.fixture.metadata(session='aux'),**self.fixture.route,
                                   is_first_turn=True,user_message=self.marker)
        request = {'messages':[{'role':'user','content':self.marker}]}
        self.fixture.runtime.check_call(request=request,**self.fixture.route,session_id='aux')
        for task in ('compression','memory_review'):
            with self.subTest(task=task),self.assertRaisesRegex(MemoryAdmissionError,'compression prompt|model history'):
                self.fixture.runtime.project_call(request=request,next_call=lambda _:self.fail('Excluded auxiliary input reached dispatch'),
                    **self.fixture.route,session_id='aux',aux_task=task)

    def test_repair_preserves_concurrent_admission_and_its_inactive_lineage(self):
        self.forget()
        ready = threading.Event()
        release = threading.Event()
        errors = []
        sent = []
        def worker():
            def trace(frame,event,arg):
                if event=='line' and frame.f_code.co_name=='_check_call' and 'states' in frame.f_locals and not ready.is_set():
                    ready.set()
                    if not release.wait(10):
                        raise RuntimeError('Concurrent admission did not release the repair')
                return trace
            sys.settrace(trace)
            try:
                runtime = MemoryRuntime(self.fixture.path)
                runtime.project_call(request={'messages':[{'role':'user','content':'Synthetic current request'}]},
                    next_call=sent.append,metadata=self.fixture.metadata(),**self.fixture.route,session_id='session')
            except Exception as error:
                errors.append(str(error))
            finally:
                sys.settrace(None)
        thread = threading.Thread(target=worker)
        thread.start()
        try:
            self.assertTrue(ready.wait(10))
            self.fixture.admit(session='concurrent-session')
        finally:
            release.set()
            thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors,[])
        self.assertEqual(len(sent),1)
        states = json.loads(self.fixture.runtime.state_path.read_text())
        self.assertEqual(set(states),{'session','concurrent-session'})
        self.fixture.runtime.clear()
        MemoryConfiguration(self.fixture.path).update(lambda config:config.update(ownership_enabled=False))
        with self.assertRaisesRegex(MemoryAdmissionError,'ownership changed for retained context'):
            self.fixture.runtime.check_call(request={},**self.fixture.route,session_id='concurrent-session')


if __name__ == '__main__':
    unittest.main()
