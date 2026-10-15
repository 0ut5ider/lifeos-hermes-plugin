# ABOUTME: Checks edits adjacent to return input capture using real private synthetic files.
# ABOUTME: Requires preparation refusal without changing later owner edits or publishing a ready plan.
import json
import sys
import unittest
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_return as fixture

class AdjacentCaptureControls(unittest.TestCase):
    def setUp(self):
        self.returned=fixture.MemoryReturnTests();self.returned.setUp()
        self.addCleanup(self.returned.doCleanups)

    def refuses(self,target,edit,expected,*,current_return):
        count=0;edited=False
        def trace(frame,event,arg):
            nonlocal count,edited
            caller=frame.f_back
            if (event=='return' and frame.f_code.co_name=='_current'
                    and frame.f_code.co_filename.endswith('/memory_export.py')
                    and caller is not None and caller.f_code.co_filename.endswith('/memory_return.py')):
                count+=1
                if count==current_return:
                    edit();edited=True
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):self.returned.prepare()
        finally:sys.settrace(None)
        self.assertTrue(edited)
        expected(target)
        self.assertFalse((self.returned.fixture.snapshot/'return').exists())

    def test_previously_absent_user_created_before_capture_is_preserved(self):
        target=self.returned.profile/'memories/USER.md';self.assertFalse(target.exists())
        later=b'Synthetic user entry created before capture.'
        self.refuses(target,lambda:target.write_bytes(later),lambda p:self.assertEqual(p.read_bytes(),later),current_return=1)

    def test_later_prompt_after_second_source_check_is_preserved(self):
        target=self.returned.profile/'SOUL.md';later=b'Synthetic unrelated later owner prompt.'
        self.refuses(target,lambda:target.write_bytes(later),lambda p:self.assertEqual(p.read_bytes(),later),current_return=2)

    def test_owner_revocation_after_second_source_check_is_preserved(self):
        target=self.returned.configuration.path;policy=json.loads(target.read_bytes())
        policy['accounts'].pop('dashboard:owner');later=(json.dumps(policy,indent=2)+'\n').encode()
        self.refuses(target,lambda:target.write_bytes(later),lambda p:self.assertEqual(p.read_bytes(),later),current_return=2)

    def test_mode_only_config_edit_after_second_source_check_is_preserved(self):
        target=self.returned.profile/'config.yaml';later_mode=(target.stat().st_mode & 0o777)^0o040
        self.refuses(target,lambda:target.chmod(later_mode),lambda p:self.assertEqual(p.stat().st_mode & 0o777,later_mode),current_return=2)
