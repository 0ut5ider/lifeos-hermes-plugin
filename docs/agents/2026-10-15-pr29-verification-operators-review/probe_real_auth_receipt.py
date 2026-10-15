# ABOUTME: Checks that a genuine other-workflow authentication receipt cannot replace recover admission.
# ABOUTME: Reuses copied safe inputs and synthetic cold bounds without writing qualification output.
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('review_binding_controls',Path(__file__).with_name('probe_certification.py'))
probes=importlib.util.module_from_spec(spec);spec.loader.exec_module(probes)
class RealReceiptControl(probes.BindingControls):
 def test_valid_normal_rollback_receipt_cannot_replace_fault_recover(self):
  actual_other=self.read('installed-normal-rollback-authentication.json')
  self.assertEqual(actual_other['status'],'PASS')
  self.assertEqual(actual_other['action'],'rollback')
  self.assertEqual(actual_other['workflow'],probes.certificate.NORMAL)
  self.write('installed-060-recovery-authentication.json',actual_other)
  with self.assertRaises(ValueError,msg='A genuine normal rollback receipt cannot prove interrupted recover admission'):
   self.cert()
if __name__=='__main__':
 suite=unittest.TestSuite([RealReceiptControl('test_valid_normal_rollback_receipt_cannot_replace_fault_recover')])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
