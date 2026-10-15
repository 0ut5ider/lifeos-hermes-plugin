# ABOUTME: Probes certification evidence bindings with copied safe receipts and actual immutable archives.
# ABOUTME: Uses synthetic cold-restore fixtures only to reach later validation, never writing a release certificate.
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
FOLDER=ROOT/'docs/verification/2026-10-15-memory-portability'
spec=importlib.util.spec_from_file_location('pinned_certificate',OUT/'source/certify_release.py')
certificate=importlib.util.module_from_spec(spec);spec.loader.exec_module(certificate)
BUILD=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/removal-workflow-packages/0.6.0-c86b5887-build.json')
DASHBOARD=Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')

class BindingControls(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.folder=Path(temp.name)
  tree=ast.parse((OUT/'source/certify_release.py').read_text())
  names={node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str)
    and node.value.endswith(('.json','.done','.stdout','.stderr')) and '/' not in node.value}
  for prefix in ('archive-integration-c86b5887','native-sealed-c86b5887','ui-archive-c86b5887'):
   names.update(prefix+suffix for suffix in ('.json','.done','.stdout','.stderr'))
  for name in names:
   path=FOLDER/name
   if path.is_file():shutil.copyfile(path,self.folder/name)
  self.synthetic_cold()
 def synthetic_cold(self):
  current=self.read('installed-060-recovery-verified.json')
  active=self.read('installed-060-update-identity.json')['result']['active']
  operations=[{'label':label,'command':['SYNTHETIC_BOUNDING_FIXTURE'],'exit_code':0}
   for label in ('backup-source','restore','disconnect','boot-offline','restored-native-verification',
    'restored-authentication','restored-version','shutdown-restore')]
  self.write('cold-restore-operations.json',operations)
  cold={'status':'PASS','source_guest':110,'restored_guest':111,'workflow':certificate.FAULT,
   'archive':'PBS-01:backup/ct/110/SYNTHETIC_NOT_AN_OBSERVATION','archive_protected':True,
   'network_disconnected':True,'software_rollback_verified':True,'active_identity':active,
   'builtin_files':current['builtin_files'],'native_consistency':{'native_consistency_signature_verified':True},
   'all_original_guest_states_preserved':True,'operations_sha256':certificate.digest(self.folder/'cold-restore-operations.json')}
  self.write('cold-restore-verification.json',cold)
  (self.folder/'cold-restore-process.done').write_text('0\n')
 def read(self,name):return json.loads((self.folder/name).read_bytes())
 def write(self,name,value):(self.folder/name).write_text(json.dumps(value,indent=2)+'\n')
 def cert(self):return certificate.certify(self.folder,BUILD,DASHBOARD)
 def test_bounding_fixture_reaches_validator_return_without_writing_certificate(self):
  result=self.cert();self.assertEqual(result['status'],'QUALIFIED')
  self.assertFalse((self.folder/'RELEASE-CERTIFICATE.json').exists())
 def test_missing_cold_receipt_refuses(self):
  (self.folder/'cold-restore-verification.json').unlink()
  with self.assertRaises(FileNotFoundError):self.cert()
 def test_later_learning_failure_requires_refusal(self):
  name='installed-stock-later-learning.json';value=self.read(name)
  value.update(actual_tool_success=False,later_fact_published=False,prior_memory_preserved=False)
  self.write(name,value)
  with self.assertRaises(ValueError,msg='QUALIFIED must not accept explicit failure of required later learning'):self.cert()
 def test_stock_recall_mismatch_requires_refusal(self):
  name='installed-stock-postboot-later-recall.json';value=self.read(name)
  value.update(marker_matched=False,expected_tool_selection=False,actual_search={'verified':False,'references':[]})
  self.write(name,value)
  with self.assertRaises(ValueError,msg='QUALIFIED must not accept explicit failure of postboot recall'):self.cert()
 def test_other_workflow_and_action_authentication_requires_refusal(self):
  name='installed-060-recovery-authentication.json';value=self.read(name)
  value.update(workflow=certificate.NORMAL,action='rollback')
  self.write(name,value)
  with self.assertRaises(ValueError,msg='QUALIFIED must bind recover authentication to the interrupted workflow'):self.cert()

if __name__=='__main__':unittest.main(verbosity=2)
