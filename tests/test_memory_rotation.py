# ABOUTME: Verifies trusted compression lineage without carrying stale LifeOS authority into a child.
# ABOUTME: Covers restart admission, native retirement, identity changes, occupied targets, and in-place compression.
import json
from concurrent.futures import ThreadPoolExecutor
import unittest

from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError, MemoryRuntime
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_runtime as runtime_fixture
import test_memory_native as native_fixture


class MemoryRotationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.saved = self.fixture.fixture.remember('Synthetic native rotation fact', 'rotation-original')
        self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route, is_first_turn=True,
                                   user_message='Synthetic admitted parent request')

    def rotate(self, child='child', parent='session', **metadata):
        return self.fixture.runtime.rotate_session(child, parent,
                                                   metadata=self.fixture.metadata(session=child, **metadata))

    def test_compression_child_keeps_verified_authority_and_can_resume(self):
        previous = json.loads(self.fixture.runtime.state_path.read_text())['session']
        self.rotate()
        self.assertEqual(self.fixture.runtime.context().session_id, 'child')
        self.fixture.runtime.check_call(request={'messages': [{'role': 'user', 'content': 'Synthetic admitted parent request'}]},
                                        **self.fixture.route, session_id='child')
        states = json.loads(self.fixture.runtime.state_path.read_text())
        self.assertEqual(states['session'], previous)
        self.assertEqual(states['child']['user_input'], previous['user_input'])
        self.fixture.runtime.clear()
        restarted = MemoryRuntime(self.fixture.path)
        restarted.admit(self.fixture.metadata(session='child'), **self.fixture.route, is_first_turn=False,
                        user_message='Synthetic verified child continuation')
        restarted.check_call(request={'messages': [{'role': 'user', 'content': 'Synthetic verified child continuation'}]},
                             **self.fixture.route, session_id='child')

    def test_in_place_compression_keeps_the_existing_binding_and_record(self):
        before = self.fixture.runtime.state_path.read_bytes()
        self.rotate(child='session')
        self.assertEqual(self.fixture.runtime.context().session_id, 'session')
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)

    def test_compression_worker_rebinds_the_caller_only_through_verified_lineage(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.rotate).result()
        self.assertEqual(self.fixture.runtime.context().session_id, 'session')
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.fixture.runtime.admit, self.fixture.metadata(session='child'),
                **self.fixture.route, is_first_turn=False, user_message='Synthetic child continuation').result()
        request = {'messages': [{'role': 'user', 'content': 'Synthetic child continuation'}]}
        sent = []
        def dispatch(projected):
            self.fixture.runtime.check_call(request=projected, **self.fixture.route, session_id='child',
                                            metadata=self.fixture.metadata(session='child'))
            sent.append(projected)
        self.fixture.runtime.project_call(request=request, next_call=dispatch, **self.fixture.route,
            session_id='child', metadata=self.fixture.metadata(session='child'))
        self.assertEqual(sent, [request])
        self.assertEqual(self.fixture.runtime.context().session_id, 'child')

    def test_an_ordinary_worker_admission_cannot_transfer_the_callers_conversation(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.fixture.runtime.admit, self.fixture.metadata(session='child'),
                **self.fixture.route, is_first_turn=True, user_message='Synthetic child continuation').result()
        with self.assertRaisesRegex(MemoryAdmissionError, 'different conversation'):
            self.fixture.runtime.project_call(request={'messages': [{'role': 'user', 'content': 'Synthetic child continuation'}]},
                next_call=lambda _: self.fail('Unverified lineage dispatched'), **self.fixture.route,
                session_id='child', metadata=self.fixture.metadata(session='child'))

    def test_compression_rebinds_an_unbound_worker_from_verified_parent_state(self):
        self.fixture.runtime.clear()
        self.rotate()
        self.assertEqual(self.fixture.runtime.context().session_id, 'child')

    def test_duplicate_rotation_keeps_the_child_and_parent_records(self):
        self.rotate()
        before = self.fixture.runtime.state_path.read_bytes()
        self.rotate()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)

    def test_a_retired_fact_after_worker_rotation_is_removed_before_foreground_dispatch(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.rotate).result()
        self.fixture.fixture.memory.forget(native_fixture.OWNER, self.saved['reference'], 'child-retirement')
        request = {'messages': [{'role': 'user', 'content': 'Synthetic admitted parent request'},
                                {'role': 'assistant', 'content': 'Synthetic native rotation fact'}]}
        sent = []
        self.fixture.runtime.project_call(request=request, next_call=sent.append, **self.fixture.route,
            session_id='child', metadata=self.fixture.metadata(session='child'))
        self.assertEqual(len(sent), 1)
        self.assertNotIn('Synthetic native rotation fact', json.dumps(sent))
        self.assertIn('Synthetic native rotation fact', json.dumps(request))

    def test_a_retired_fact_after_worker_rotation_cannot_dispatch_an_auxiliary_call(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.rotate).result()
        self.fixture.fixture.memory.forget(native_fixture.OWNER, self.saved['reference'], 'child-retirement')
        with self.assertRaises(MemoryAdmissionError):
            self.fixture.runtime.project_call(request={'messages': [{'role': 'user', 'content': 'Synthetic admitted parent request'}]},
                next_call=lambda _: self.fail('Stale child dispatched'), **self.fixture.route,
                session_id='child', metadata=self.fixture.metadata(session='child'), aux_task='compression')

    def test_compression_refuses_a_missing_parent_and_preserves_state(self):
        before = self.fixture.runtime.state_path.read_bytes()
        with self.assertRaisesRegex(MemoryAdmissionError, 'parent'):
            self.rotate(parent='unknown-parent')
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)

    def test_compression_refuses_changed_author_and_missing_current_destination(self):
        before = self.fixture.runtime.state_path.read_bytes()
        for metadata in (self.fixture.metadata(session='child', user='other'), {}, self.fixture.metadata()):
            with self.subTest(metadata=metadata), self.assertRaises(MemoryAdmissionError):
                self.fixture.runtime.rotate_session('child', 'session', metadata=metadata)
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)

    def test_compression_refuses_stale_native_fact_generation(self):
        self.fixture.fixture.memory.forget(native_fixture.OWNER, self.saved['reference'], 'rotation-forget')
        before = self.fixture.runtime.state_path.read_bytes()
        with self.assertRaisesRegex(MemoryAdmissionError, 'invalidated memory context'):
            self.rotate()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)

    def test_compression_refuses_changed_permissions(self):
        self.fixture.configuration['destinations']['chat-a:200']['write'] = []
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        before = self.fixture.runtime.state_path.read_bytes()
        with self.assertRaises(MemoryAdmissionError):
            self.rotate()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)

    def test_compression_cannot_overwrite_another_conversations_saved_proof(self):
        self.fixture.runtime.admit(self.fixture.metadata(session='child'), **self.fixture.route, is_first_turn=True,
                                   user_message='Synthetic different admitted request')
        self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route, is_first_turn=False,
                                   user_message='Synthetic admitted parent request')
        before = self.fixture.runtime.state_path.read_bytes()
        with self.assertRaisesRegex(MemoryAdmissionError, 'different conversation'):
            self.rotate()
        self.assertEqual(self.fixture.runtime.state_path.read_bytes(), before)
