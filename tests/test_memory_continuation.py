# ABOUTME: Checks actual Hermes continuation prompts against recorded owner input proofs.
# ABOUTME: Keeps generated user-role text within retained-history policy and preserves original requests.
from copy import deepcopy
import os
from pathlib import Path
import sys
import unittest
import test_memory_history as fixture
from lifeos_hook_bridge.memory_history import REMOVED
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError


class MemoryContinuationTests(unittest.TestCase):
    def setUp(self):
        self.history = fixture.MemoryHistoryTests()
        self.history.setUp()
        self.addCleanup(self.history.doCleanups)
        self.fixture = self.history.fixture
        self.marker = self.history.marker
        source = os.environ['LIFEOS_HERMES_SOURCE']
        sys.path.insert(0, source)
        self.addCleanup(sys.path.remove, source)
        from agent.context_compressor import ContextCompressor
        from agent.conversation_loop import _get_continuation_prompt
        self.continuation = _get_continuation_prompt(False)
        self.classifier = ContextCompressor._is_synthetic_compression_user_turn
        self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route, is_first_turn=True,
            user_message='Synthetic admitted continuation task')

    def project(self, request): return self.history.project(request)

    def forget(self): return self.history.forget()

    def request(self, nudge=None):
        return {'messages': [{'role': 'user', 'content': 'Synthetic admitted continuation task'},
            {'role': 'assistant', 'content': 'Synthetic partial output'},
            {'role': 'user', 'content': self.continuation if nudge is None else nudge}]}

    def test_actual_generated_continuation_preserves_original_proof_and_request(self):
        request = self.request()
        original = deepcopy(request)
        result = self.project(request)
        self.assertEqual(result, original)
        self.assertEqual(request, original)
        self.fixture.runtime.check_call(request=result, **self.fixture.route, session_id='session')

    def test_generated_user_tail_is_filtered_and_never_treated_as_an_explicit_quote(self):
        self.forget()
        from agent.conversation_loop import _LENGTH_CONTINUATION_DROPPED_TOOLS_PREFIX
        nudge = _LENGTH_CONTINUATION_DROPPED_TOOLS_PREFIX + self.marker
        self.assertTrue(self.classifier({'role': 'user', 'content': nudge}))
        request = self.request(nudge)
        result = self.project(request)
        self.assertEqual(result['messages'][0], request['messages'][0])
        self.assertEqual(result['messages'][2]['content'], REMOVED)
        with self.assertRaisesRegex(MemoryAdmissionError, 'model history'):
            self.fixture.runtime.check_call(request=request, **self.fixture.route, session_id='session')

    def test_arbitrary_later_input_cannot_borrow_the_previous_input_proof(self):
        with self.assertRaisesRegex(MemoryAdmissionError, 'verify the current user input'):
            self.project(self.request('Synthetic different human task'))

    def test_missing_original_input_and_changed_continuation_refuse(self):
        for request in ({'messages': [{'role': 'user', 'content': self.continuation}]},
                self.request(self.continuation + ' Synthetic extra instruction')):
            with self.subTest(request=request), self.assertRaisesRegex(MemoryAdmissionError, 'verify the current user input'):
                self.project(request)


    def test_generated_responses_blocks_filter_the_derived_tail_and_keep_the_original_quote(self):
        from agent.conversation_loop import _LENGTH_CONTINUATION_DROPPED_TOOLS_PREFIX
        original = [{'type': 'input_text', 'text': self.marker}]
        self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route, is_first_turn=True,
            user_message=original)
        self.forget()
        request = {'input': [{'role': 'user', 'content': original},
            {'role': 'assistant', 'content': 'Synthetic partial output'},
            {'role': 'user', 'content': [{'type': 'input_text',
                'text': _LENGTH_CONTINUATION_DROPPED_TOOLS_PREFIX + self.marker}]}]}
        result = self.project(request)
        self.assertEqual(result['input'][0]['content'], original)
        self.assertEqual(result['input'][2]['content'][0]['text'], REMOVED)
        self.fixture.runtime.check_call(request=result, **self.fixture.route, session_id='session')

    def test_actual_human_input_that_matches_a_native_nudge_keeps_its_recorded_proof(self):
        for content in (self.continuation, REMOVED):
            with self.subTest(content=content):
                self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route, is_first_turn=True,
                    user_message=content)
                request = {'messages': [{'role': 'user', 'content': content}]}
                self.assertEqual(self.project(request), request)
