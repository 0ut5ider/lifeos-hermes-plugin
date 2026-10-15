# ABOUTME: Closes certification proof and authentication defects against exact corrected sources.
# ABOUTME: Uses temporary synthetic cold and review bounds, actual archives, and safe copied evidence only.
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
prior=ROOT/'docs/agents/2026-10-15-pr29-verification-operators-review/probe_certification.py'
spec=importlib.util.spec_from_file_location('original_binding_controls',prior)
probes=importlib.util.module_from_spec(spec);spec.loader.exec_module(probes)
EVENTS=OUT/'independent-cases.jsonl'

class ClosureControls(probes.BindingControls):
 def setUp(self):
  super().setUp()
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.repo=Path(temp.name)
  target=self.repo/'docs/verification/2026-10-15-memory-portability';target.mkdir(parents=True)
  for path in self.folder.iterdir():shutil.copyfile(path,target/path.name)
  for path in (OUT/'source').glob('*.py'):shutil.copyfile(path,target/path.name)
  self.folder=target
  module_spec=importlib.util.spec_from_file_location('corrected_certificate_'+self.id().split('.')[-1],target/'certify_release.py')
  self.module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(self.module)
  self.report=self.repo/'docs/agents/synthetic-review.md';self.report.parent.mkdir(parents=True)
  self.report.write_text('Synthetic validator fixture. This is not operational acceptance.\nReview status: CLEAR\n')
  prefix='docs/verification/2026-10-15-memory-portability/'
  self.closure={'status':'CLEAR','report':str(self.report.relative_to(self.repo)),
   'report_sha256':self.module.digest(self.report),
   'source_sha256':{prefix+name:self.module.digest(target/name) for name in self.module.OPERATORS}}
  self.write('operator-review-closure.json',self.closure)
 def cert(self):return self.module.certify(self.folder,probes.BUILD,probes.DASHBOARD)
 def record(self,case,result,detail=''):
  with EVENTS.open('a') as stream:stream.write(json.dumps({'case':case,'result':result,'detail':detail})+'\n')
 def rejects_field(self,name,path,replacement):
  original=self.read(name);changed=copy.deepcopy(original);value=changed
  for key in path[:-1]:value=value[key]
  value[path[-1]]=replacement;self.write(name,changed)
  case=name+':'+'.'.join(path)
  try:
   try:self.cert()
   except ValueError as error:self.record(case,'REFUSED',str(error))
   else:
    self.record(case,'FALSE_QUALIFIED')
    self.fail('Qualification accepts failed evidence '+case)
  finally:self.write(name,original)
 def test_genuine_normal_rollback_receipt_cannot_prove_fault_recover(self):
  self.write('installed-060-recovery-authentication.json',self.read('installed-normal-rollback-authentication.json'))
  with self.assertRaisesRegex(ValueError,'another workflow or action'):self.cert()
 def test_each_decisive_learning_and_recall_flag_refuses_independently(self):
  cases=[]
  for flag in ('actual_tool_success','later_fact_published','prior_memory_preserved','exact_tool_selection'):
   cases.append(('installed-stock-later-learning.json',[flag],False))
  for name in ('installed-stock-builtin-recall.json','installed-stock-postboot-later-recall.json','installed-postrollback-later-recall.json'):
   for flag in ('marker_matched','expected_tool_selection','configured_route_used'):
    cases.append((name,[flag],False))
   cases.extend([(name,['actual_search','verified'],False),(name,['tool_names'],['unexpected_tool'])])
  cases.extend([('installed-new-native-fact-builtin-recall.json',['actual_proof'],False),
   ('installed-new-native-fact-builtin-recall.json',['tool_names'],['unexpected_tool'])])
  for flag in ('actual_proof','exact_arguments'):
   cases.append(('installed-new-native-learning.json',[flag],False))
  cases.extend([('installed-new-native-learning.json',['tool_names'],[]),
   ('installed-new-native-recall.json',['actual_proof'],False),
   ('installed-new-native-recall.json',['actual_search','verified'],False),
   ('installed-new-native-recall.json',['tool_names'],[])])
  for flag in ('original_source_digest_matches','exact_tool_selection','actual_tool_ok','exact_reference'):
   cases.append(('installed-imported-fact-pass.json',[flag],False))
  for name,path,value in cases:
   with self.subTest(receipt=name,field=path):self.rejects_field(name,path,value)
 def test_each_authentication_workflow_and_action_refuses_independently(self):
  cases=[('installed-060-recovery-authentication.json',['workflow'],self.module.NORMAL),
   ('installed-060-recovery-authentication.json',['action'],'rollback'),
   ('installed-normal-rollback-authentication.json',['workflow'],self.module.FAULT),
   ('installed-normal-rollback-authentication.json',['action'],'recover'),
   ('installed-stock-wrong-password-refusal.json',['workflow'],self.module.FAULT),
   ('installed-stock-wrong-password-refusal.json',['action'],'recover')]
  for name,path,value in cases:
   with self.subTest(receipt=name,field=path):self.rejects_field(name,path,value)
 def test_missing_review_closure_refuses_full_certification(self):
  (self.folder/'operator-review-closure.json').unlink()
  with self.assertRaises(FileNotFoundError):self.cert()
 def test_matching_review_closure_is_returned_by_full_certification(self):
  result=self.cert()
  self.assertEqual(result['verification_operator_review'],self.closure)
  self.assertEqual(result['qualification_receipt_sha256']['operator-review-closure.json'],
   self.module.digest(self.folder/'operator-review-closure.json'))
  self.assertFalse((self.folder/'RELEASE-CERTIFICATE.json').exists())
 def test_nonclear_review_closure_refuses(self):
  self.write('operator-review-closure.json',{**self.closure,'status':'PENDING'})
  with self.assertRaisesRegex(ValueError,'not clear'):self.module.review_closure(self.folder)
 def test_stale_report_hash_refuses(self):
  self.report.write_text(self.report.read_text()+'A later report edit.\n')
  with self.assertRaisesRegex(ValueError,'does not match'):self.module.review_closure(self.folder)
 def test_nonclear_report_with_matching_hash_refuses(self):
  self.report.write_text('Review status: CORRECTION_REQUIRED\n')
  self.closure['report_sha256']=self.module.digest(self.report)
  self.write('operator-review-closure.json',self.closure)
  with self.assertRaisesRegex(ValueError,'does not match'):self.module.review_closure(self.folder)
 def test_incomplete_operator_coverage_refuses(self):
  self.closure['source_sha256'].pop(next(iter(self.closure['source_sha256'])))
  self.write('operator-review-closure.json',self.closure)
  with self.assertRaisesRegex(ValueError,'every verification operator'):self.module.review_closure(self.folder)
 def test_additional_unreviewed_operator_coverage_refuses(self):
  self.closure['source_sha256']['docs/verification/2026-10-15-memory-portability/unreviewed.py']='0'*64
  self.write('operator-review-closure.json',self.closure)
  with self.assertRaisesRegex(ValueError,'every verification operator'):self.module.review_closure(self.folder)
 def test_changed_operator_source_refuses(self):
  target=self.folder/'verify_restored_removal.py';target.write_text(target.read_text()+'\n# synthetic later edit\n')
  with self.assertRaisesRegex(ValueError,'changes after'):self.module.review_closure(self.folder)
 def test_wrong_source_digest_refuses(self):
  self.closure['source_sha256'][next(iter(self.closure['source_sha256']))]='0'*64
  self.write('operator-review-closure.json',self.closure)
  with self.assertRaisesRegex(ValueError,'changes after'):self.module.review_closure(self.folder)
 def test_report_outside_agent_records_refuses(self):
  self.closure['report']='docs/verification/2026-10-15-memory-portability/certify_release.py'
  self.write('operator-review-closure.json',self.closure)
  with self.assertRaisesRegex(ValueError,'outside'):self.module.review_closure(self.folder)

if __name__=='__main__':
 EVENTS.write_text('')
 unittest.main(verbosity=2)
