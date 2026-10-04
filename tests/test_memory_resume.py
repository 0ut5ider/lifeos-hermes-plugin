# ABOUTME: Checks resumed conversation repair against current native retirement and identity state.
# ABOUTME: Preserves audience, route, and prompt admission while rebuilding readable request history.
from dataclasses import replace
import json
import unittest

from lifeos_hook_bridge.memory_history import REMOVED
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError, MemoryRuntime
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_runtime as runtime_fixture
import test_memory_native as native_fixture


class MemoryResumeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.marker = 'Synthetic retired resumed conversation claim'
        self.saved = self.fixture.fixture.remember(self.marker, 'resume-original')
        self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route,
                                   is_first_turn=True, user_message='Synthetic first request')

    def retire(self):
        self.fixture.fixture.memory.forget(native_fixture.OWNER, self.saved['reference'], 'resume-forget')

    def resume(self, message='Synthetic resumed request'):
        self.fixture.runtime.clear()
        runtime = MemoryRuntime(self.fixture.path)
        runtime.admit(self.fixture.metadata(), **self.fixture.route, is_first_turn=False, user_message=message)
        return runtime

    def project(self, runtime, request):
        sent = []
        def dispatch(projected):
            runtime.check_call(request=projected, **self.fixture.route, session_id='session')
            sent.append(projected)
        runtime.project_call(request=request, next_call=dispatch, **self.fixture.route, session_id='session')
        self.assertEqual(len(sent), 1)
        return sent[0]

    def test_resume_repairs_retired_chat_history_before_the_next_request(self):
        self.retire()
        runtime = self.resume()
        result = self.project(runtime, {'messages': [
            {'role': 'assistant', 'content': self.marker},
            {'role': 'user', 'content': 'Synthetic resumed request'}]})
        self.assertEqual(result['messages'][0]['content'], REMOVED)
        self.assertEqual(result['messages'][1]['content'], 'Synthetic resumed request')
        restarted = self.resume()
        self.assertEqual(self.project(restarted, result), result)

    def test_resume_repairs_corrected_responses_history_and_keeps_the_current_receipt(self):
        replacement = 'Synthetic current resumed conversation claim'
        corrected = self.fixture.fixture.memory.correct(native_fixture.OWNER, self.saved['reference'],
                                                         replacement, 'resume-correct')
        runtime = self.resume()
        result = self.project(runtime, {'input': [
            {'type': 'function_call', 'call_id': 'call-one', 'name': 'read_context', 'arguments': '{}'},
            {'type': 'function_call_output', 'call_id': 'call-one',
             'output': json.dumps({'content': self.marker, 'reference': self.saved['reference']})},
            {'role': 'assistant', 'content': json.dumps(corrected)},
            {'role': 'user', 'content': 'Synthetic resumed request'}]})
        self.assertNotIn(self.marker, json.dumps(result))
        self.assertEqual(json.loads(result['input'][1]['output'])['reference'], self.saved['reference'])
        self.assertEqual(result['input'][0]['call_id'], result['input'][1]['call_id'])
        self.assertEqual(result['input'][2]['content'], json.dumps(corrected))

    def test_resumed_explicit_quote_does_not_authorize_appended_recall(self):
        self.retire()
        runtime = self.resume(self.marker)
        result = self.project(runtime, {'messages': [
            {'role': 'user', 'content': self.marker + '\nAppended recall: ' + self.marker}]})
        self.assertEqual(result['messages'][0]['content'], self.marker + REMOVED)

    def test_resumed_auxiliary_call_remains_blocked_until_foreground_history_is_repaired(self):
        self.retire()
        runtime = self.resume()
        with self.assertRaisesRegex(MemoryAdmissionError, 'invalidated memory context'):
            runtime.project_call(request={'messages': [{'role': 'user', 'content': 'Synthetic generated summary'}]},
                                 next_call=lambda _: self.fail('Auxiliary dispatch reached'),
                                 **self.fixture.route, session_id='session', aux_task='compression')

    def test_resume_refuses_changed_owner_authority_and_preserves_the_recorded_state(self):
        self.retire()
        self.fixture.configuration['accounts'] = {}
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        previous = self.fixture.runtime.state_path.read_bytes()
        with self.assertRaisesRegex(MemoryAdmissionError, 'identity binding'):
            self.resume()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), previous)

    def test_resume_refuses_changed_prompt_before_it_rewrites_history(self):
        self.retire()
        (self.fixture.home / 'SOUL.md').write_text('# Synthetic changed installed prompt\n')
        previous = self.fixture.runtime.state_path.read_bytes()
        with self.assertRaisesRegex(MemoryAdmissionError, 'current facts changed'):
            self.resume()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), previous)

    def apply_identity_proposal(self):
        scope = replace(native_fixture.OWNER, proposals=('create', 'review', 'approve'))
        native = self.fixture.fixture
        (native.root / 'LIFEOS/PULSE').symlink_to(native_fixture.SOURCE / 'LIFEOS/PULSE')
        target = native.root / 'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# Synthetic operating rules\n')
        item = {'type': 'proposal', 'target_kind': 'operational-rule', 'target_file': str(target),
                'edit': 'Confirm synthetic ownership before publication.', 'confidence': 0.5,
                'rationale': 'Synthetic owner rule.'}
        proposal = native.memory.native_add(scope, item, request_id='resume-identity-proposal', project='')
        self.assertTrue(proposal['ok'], proposal)
        result = native.memory.decide_proposal(scope, proposal['receipt']['proposal_reference'],
                                              'accept', 'resume-identity-accept')
        self.assertEqual(result['status'], 'committed', result)

    def test_request_projection_cannot_refresh_an_applied_identity_proposal(self):
        self.apply_identity_proposal()
        with self.assertRaisesRegex(MemoryAdmissionError, 'invalidated memory context'):
            self.project(self.fixture.runtime, {'messages': [{'role': 'user', 'content': 'Synthetic first request'}]})

    def test_resume_requires_verified_proposal_state(self):
        states = json.loads(self.fixture.runtime.state_path.read_text())
        states['session'].pop('proposal_generation', None)
        self.fixture.runtime.state_path.write_text(json.dumps(states))
        with self.assertRaisesRegex(MemoryAdmissionError, 'current facts changed'):
            self.resume()

    def test_failed_history_repair_preserves_the_stale_admission(self):
        self.retire()
        runtime = self.resume()
        previous = runtime.state_path.read_bytes()
        with self.assertRaisesRegex(MemoryAdmissionError, 'model history'):
            self.project(runtime, {'input': [
                {'type': 'function_call', 'call_id': self.marker, 'name': 'read_context', 'arguments': '{}'},
                {'role': 'user', 'content': 'Synthetic resumed request'}]})
        self.assertEqual(runtime.state_path.read_bytes(), previous)
        with self.assertRaisesRegex(MemoryAdmissionError, 'invalidated memory context'):
            runtime.check_call(request={}, **self.fixture.route, session_id='session')

    def test_identity_proposal_after_resume_blocks_fact_repair(self):
        self.retire()
        runtime = self.resume()
        self.apply_identity_proposal()
        with self.assertRaisesRegex(MemoryAdmissionError, 'invalidated memory context'):
            self.project(runtime, {'messages': [
                {'role': 'assistant', 'content': self.marker},
                {'role': 'user', 'content': 'Synthetic resumed request'}]})
