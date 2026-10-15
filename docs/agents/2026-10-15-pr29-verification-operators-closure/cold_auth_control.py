# ABOUTME: Tests a genuine recover-admission receipt substituted for cold rollback authentication.
# ABOUTME: Keeps other cold bounds explicitly synthetic and does not claim an actual restored-guest observation.
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('closure_probe',Path(__file__).with_name('closure_controls.py'))
closure=importlib.util.module_from_spec(spec);spec.loader.exec_module(closure)
class ColdAuthControl(closure.ClosureControls):
 def test_genuine_fault_recover_auth_cannot_prove_cold_rollback(self):
  recover=self.read('installed-060-recovery-authentication.json')
  self.assertEqual(recover['status'],'PASS');self.assertEqual(recover['action'],'recover')
  cold=self.read('cold-restore-verification.json')
  cold['retained_helper_authentication']=recover
  self.write('cold-restore-verification.json',cold)
  with self.assertRaises(ValueError,msg='Fault recover admission cannot prove cold restored rollback authentication'):
   self.cert()
if __name__=='__main__':
 suite=unittest.TestSuite([ColdAuthControl('test_genuine_fault_recover_auth_cannot_prove_cold_rollback')])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
