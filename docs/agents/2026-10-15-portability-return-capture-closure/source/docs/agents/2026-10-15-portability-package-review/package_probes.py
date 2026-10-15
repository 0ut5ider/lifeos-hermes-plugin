# ABOUTME: Reviews package-wide current-state bindings using synthetic data and actual profile services.
# ABOUTME: Refuses lost edits across transformation and target capture without changing product source.
import json
import sys
import unittest
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_return as return_fixture
import test_profile_services as service_fixture
from lifeos_hook_bridge.memory_transition import MemoryTransition


class ReturnCaptureControls(unittest.TestCase):
    def setUp(self):
        self.returned=return_fixture.MemoryReturnTests();self.returned.setUp();self.addCleanup(self.returned.doCleanups)
        self.profile=self.returned.profile;self.services=service_fixture.ProfileServicesTests()
        self.services.fixture_home=self.returned.fixture.fixture.fixture.home;self.services.fixture_profile=self.profile
        self.services.setUp();self.addCleanup(self.services.doCleanups)

    def apply_after_edit(self,target,later):
        edited=False
        def trace(frame,event,arg):
            nonlocal edited
            if (not edited and event=='return' and frame.f_code.co_name=='_configuration'
                    and frame.f_code.co_filename.endswith('/memory_return.py')):
                target.write_bytes(later);edited=True
            return trace
        sys.settrace(trace)
        try:
            try:prepared=self.returned.prepare()
            except MemoryUnavailable:prepared=None
        finally:sys.settrace(None)
        self.assertTrue(edited)
        if prepared is not None:
            transition=MemoryTransition(self.returned.configuration,units=self.services.units)
            review=transition.prepare_return(self.returned.fixture.snapshot,prepared['signature'],account='dashboard:owner')
            transition.apply(review['signature'],account='dashboard:owner')
        if prepared is None:self.assertEqual(target.read_bytes(),later)

    def test_config_edit_after_transform_is_preserved(self):
        target=self.profile/'config.yaml'
        self.apply_after_edit(target,target.read_bytes()+b'synthetic_later_owner_setting: keep\n')
        from ruamel.yaml import YAML
        self.assertEqual(YAML(typ='safe').load(target.read_bytes()).get('synthetic_later_owner_setting'),'keep',
            'Return publication loses the later unrelated owner setting')

    def test_policy_edit_after_transform_is_preserved(self):
        target=self.returned.configuration.path
        selected=json.loads(target.read_bytes());selected['accounts']['synthetic:later-owner-account']='owner'
        self.apply_after_edit(target,(json.dumps(selected,indent=2)+'\n').encode())
        self.assertEqual(json.loads(target.read_bytes())['accounts'].get('synthetic:later-owner-account'),'owner',
            'Return publication loses the later unrelated identity grant')


class PreCaptureSourceControls(ReturnCaptureControls):
    def test_builtin_source_edit_before_input_capture_is_preserved(self):
        target=self.profile/'memories/MEMORY.md'
        later=target.read_bytes()+b'\n\xc2\xa7\nSynthetic later builtin fact before return capture.';edited=False
        def trace(frame,event,arg):
            nonlocal edited
            caller=frame.f_back
            if (not edited and event=='return' and frame.f_code.co_name=='_current'
                    and frame.f_code.co_filename.endswith('/memory_export.py') and caller is not None
                    and caller.f_code.co_filename.endswith('/memory_return.py')):
                target.write_bytes(later);edited=True
            return trace
        sys.settrace(trace)
        try:
            try:prepared=self.returned.prepare()
            except MemoryUnavailable:prepared=None
        finally:sys.settrace(None)
        self.assertTrue(edited)
        if prepared is not None:
            transition=MemoryTransition(self.returned.configuration,units=self.services.units)
            review=transition.prepare_return(self.returned.fixture.snapshot,prepared['signature'],account='dashboard:owner')
            transition.apply(review['signature'],account='dashboard:owner')
        self.assertIn(b'Synthetic later builtin fact before return capture.',target.read_bytes(),
            'A source entry written after the export current check is silently replaced by the older export')
