# ABOUTME: Characterizes program fingerprint overrides and retained-edit protection with synthetic files.
# ABOUTME: Uses the actual product checker without reading live journals, personal records, or private maps.
import hashlib,importlib.util,json,os,shutil,tempfile
from pathlib import Path
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent;s=p/'optional/lifeos_release_manager/release_programs.py'
spec=importlib.util.spec_from_file_location('review_programs',s);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
results=[]
with tempfile.TemporaryDirectory(prefix='program-semantics-',dir=r) as tmp:
 root=Path(tmp);root.chmod(0o700)
 for label in ['unchanged-release','direct-file-owner-mount','nested-file-override-is-not-directory-override','unrelated-directory-edit-refuses','retained-before-edit-refuses','blind-current-directory-override-accepts-unrelated-edit']:
  case=root/label;case.mkdir();snapshot=case/'snapshot';snapshot.mkdir();plugin=case/'plugin';plugin.mkdir();config=case/'config.yaml'
  config.write_text('synthetic release configuration\n');(plugin/'program.py').write_text('synthetic release program\n')
  beforefile=snapshot/'before-0';beforefile.write_text('synthetic prior configuration\n')
  beforedir=snapshot/'before-1';beforedir.mkdir();(beforedir/'program.py').write_text('synthetic prior program\n')
  entries=[{'target':str(config),'allow_links':False,'before':module.fingerprint(beforefile),'after':module.fingerprint(config)}, {'target':str(plugin),'allow_links':False,'before':module.fingerprint(beforedir),'after':module.fingerprint(plugin)}]
  overrides={}
  if label=='direct-file-owner-mount':
   config.write_text('synthetic owner mount\n');overrides[str(config)]=module.fingerprint(config)
  if label=='nested-file-override-is-not-directory-override':
   (plugin/'program.py').write_text('synthetic owner mount output\n');overrides[str(plugin/'program.py')]=module.fingerprint(plugin/'program.py')
  if label in ['unrelated-directory-edit-refuses','blind-current-directory-override-accepts-unrelated-edit']:
   (plugin/'unexpected.txt').write_text('synthetic unrelated edit\n')
  if label=='retained-before-edit-refuses':beforefile.write_text('synthetic later retained edit\n')
  if label=='blind-current-directory-override-accepts-unrelated-edit':overrides[str(plugin)]=module.fingerprint(plugin)
  class Transaction(module.ProgramTransaction):
   def _load(self):return {'state':'applied','entries':entries}
  accepted=True;error=None
  try:Transaction(snapshot).check_applied(overrides=overrides)
  except module.ProgramConflict as exc:accepted=False;error=str(exc)
  expected=label in ['unchanged-release','direct-file-owner-mount','blind-current-directory-override-accepts-unrelated-edit']
  assert accepted==expected,label
  results.append({'case':label,'accepted':accepted,'error':error,'expected_behavior_verified':True,'scope':'Actual checker and fingerprints, synthetic _load boundary and actual synthetic files only'})
report={'status':'PASS','cases':results,'product_checker_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'remote_calls':False,'live_journals_read':False,'guest_receipts_written':False}
(r/'program-mount-semantics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
