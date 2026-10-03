# ABOUTME: Tests memory admission and retained-context invalidation with native fixtures.
# ABOUTME: Covers app-neutral author binding, route changes, forget operations, and restart.
from dataclasses import asdict
import json
import os
from pathlib import Path
import unittest
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_runtime import MemoryRuntime, MemoryAdmissionError
import test_memory_native as native_fixture

class MemoryRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home = self.fixture.home / 'hermes'
        self.route = dict(provider='synthetic', model='synthetic-model', base_url='http://127.0.0.1/v1', api_mode='chat_completions')
        fingerprint = route_identity(**self.route)
        grant = {'visibility':'private','participants':['owner'],'read':['principal','assistant','project'],
                 'write':['principal','assistant','project'],'projects':['*'],'model_routes':[fingerprint]}
        self.configuration = {'version':1,'root':str(self.fixture.root),'principal':'owner','ownership_enabled':True,
                              'accounts':{'chat-a:100':'owner','chat-b:300':'owner'},
                              'destinations':{'chat-a:200':grant,'chat-b:400':grant},'sharing_enabled':False,'clients':{}}
        self.path = self.home / 'lifeos-memory.json'
        MemoryConfiguration(self.path).save(self.configuration)
        self.runtime = MemoryRuntime(self.path)
    def metadata(self, app='chat-a', user='100', destination='200', session='session', **changes):
        result = {'HERMES_SESSION_PLATFORM':app,'HERMES_SESSION_USER_ID':user,'HERMES_SESSION_CHAT_ID':destination,
                  'HERMES_SESSION_CHAT_TYPE':'dm','HERMES_SESSION_ID':session}
        return dict(result, **changes)
    def admit(self, **changes):
        return self.runtime.admit(self.metadata(**changes), **self.route, is_first_turn=True)
    def test_different_apps_bind_their_authenticated_authors(self):
        self.admit()
        first = self.runtime.context()
        self.runtime.check_call(request={'model':'synthetic-model'}, **self.route, session_id='session')
        self.admit(app='chat-b',user='300',destination='400',session='other')
        second = self.runtime.context()
        self.assertEqual(first.participants, second.participants)
        self.assertEqual((first.author, second.author), ('100','300'))
    def test_unknown_shared_author_and_schedule_are_blocked_before_hooks(self):
        for metadata in [self.metadata(user='other'), self.metadata(HERMES_SESSION_CHAT_TYPE='channel'),
                         self.metadata(HERMES_CRON_SESSION='1', HERMES_CRON_AUTO_DELIVER_PLATFORM='chat-a', HERMES_CRON_AUTO_DELIVER_CHAT_ID='200')]:
            with self.subTest(metadata=metadata), self.assertRaises(MemoryAdmissionError):
                self.runtime.admit(metadata, **self.route, is_first_turn=True)
            self.assertIsNone(self.runtime.context())
    def test_actual_endpoint_and_request_model_cannot_borrow_parent_approval(self):
        self.admit()
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **dict(self.route, base_url='https://example.com/v1'), session_id='session')
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={'model':'cloud-model'}, **self.route, session_id='session')
    def test_forgetting_invalidates_existing_context_across_restart(self):
        saved = self.fixture.remember()
        self.admit()
        self.fixture.memory.forget(native_fixture.OWNER, saved['reference'], 'forget')
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='session')
        other = MemoryRuntime(self.path)
        with self.assertRaises(MemoryAdmissionError):
            other.admit(self.metadata(), **self.route, is_first_turn=False)
        other.admit(self.metadata(session='fresh'), **self.route, is_first_turn=True)
    def test_resumed_history_needs_a_recorded_matching_admission(self):
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.admit(self.metadata(), **self.route, is_first_turn=False)
        self.admit()
        other = MemoryRuntime(self.path)
        other.admit(self.metadata(), **self.route, is_first_turn=False)
        other.check_call(request={}, **self.route, session_id='session')
    def test_revocation_changes_the_current_grant(self):
        self.admit()
        self.configuration['accounts'] = {}
        MemoryConfiguration(self.path).save(self.configuration)
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='session')
    def test_native_hook_environment_replaces_untrusted_context_and_recursion_flag(self):
        self.admit()
        environment = {'LIFEOS_MEMORY_CONTEXT':json.dumps({'author':'other'}),'LIFEOS_MEMORY_INTERNAL':'1'}
        self.runtime.bind_environment(environment)
        self.assertEqual(json.loads(environment['LIFEOS_MEMORY_CONTEXT']), json.loads(json.dumps(asdict(self.runtime.context()))))
        self.assertNotIn('LIFEOS_MEMORY_INTERNAL',environment)
    def test_inactive_configuration_does_not_restrict_existing_memory_setup(self):
        self.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.path).save(self.configuration)
        self.runtime.admit({}, **self.route, is_first_turn=False)
        self.runtime.check_call(request={}, **self.route, session_id='missing')
        self.assertIsNone(self.runtime.context())

    def test_inactive_admission_accepts_a_host_without_new_route_metadata(self):
        self.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.path).save(self.configuration)
        self.runtime.admit({})
        self.assertIsNone(self.runtime.context())

    def test_terminal_platform_comes_from_host_when_gateway_metadata_is_empty(self):
        import os
        route = route_identity(**self.route)
        self.configuration['accounts'][f'terminal:{os.getuid()}'] = 'owner'
        self.configuration['destinations'][f'terminal:{self.home}'] = {
            'visibility':'private','participants':['owner'],'read':['principal','assistant','project'],
            'write':['project'],'projects':['*'],'model_routes':[route]}
        MemoryConfiguration(self.path).save(self.configuration)
        self.runtime.admit({'HERMES_SESSION_PLATFORM':''}, **self.route, platform='cli', session_id='terminal', is_first_turn=True)
        self.assertEqual(self.runtime.context().transport,'terminal')

    def test_separate_hook_process_rebinds_only_a_recorded_current_context(self):
        from unittest.mock import patch
        self.admit()
        context = self.runtime.context()
        environment = {'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(context))}
        self.runtime.clear()
        with patch.dict(os.environ, environment):
            self.runtime.check_call(request={}, **self.route, session_id='session')
        self.runtime.clear()
        environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(dict(asdict(context),session_id='unrecorded'))
        with patch.dict(os.environ, environment), self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='unrecorded')

    def test_unknown_host_route_cannot_be_approved_as_private(self):
        self.configuration['destinations']['chat-a:200']['model_routes'] = ['unknown']
        MemoryConfiguration(self.path).save(self.configuration)
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.admit(self.metadata(),provider='',model='',base_url='',api_mode='',is_first_turn=True)

    def test_disable_or_remove_configuration_cannot_release_retained_private_context(self):
        self.admit()
        self.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.path).save(self.configuration)
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='session')
        self.path.unlink()
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='session')
        self.runtime.clear()
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='session')

    def test_changed_author_cannot_use_a_previous_worker_admission(self):
        self.admit()
        self.runtime.clear()
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.check_call(request={}, **self.route, session_id='session', metadata=self.metadata(user='other'))
