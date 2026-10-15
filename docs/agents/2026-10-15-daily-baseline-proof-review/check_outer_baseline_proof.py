# ABOUTME: Checks baseline proof file boundaries and race refusals using only synthetic private fixtures.
# ABOUTME: Executes the actual helper and preserves every test output without accessing daily files.
import copy,hashlib,importlib.util,json,os,tempfile
from pathlib import Path
from types import SimpleNamespace
r=Path(__file__).resolve().parent;s=r/'source/prove_daily_baseline.py'
spec=importlib.util.spec_from_file_location('review_baseline_proof',s);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
catalog=json.loads((s.parent/'daily-baseline-public-programs.json').read_bytes())
labels=['positive','missing-entry','duplicate-entry','wrong-kind','wrong-source','wrong-target','current-mount-collision','baseline-mode','baseline-symlink','baseline-hardlink','baseline-owner','intent-mode','intent-symlink','intent-hardlink','intent-owner','intent-action','intent-extra-field','intent-malformed-prior','intent-too-large','intent-too-early','baseline-changed-during-proof','intent-changed-during-proof']
results=[]
with tempfile.TemporaryDirectory(prefix='outer-proof-',dir=r) as tmp:
 for label in labels:
  root=Path(tmp)/label;home=root/'owner';installed=home/'.claude';installed.mkdir(parents=True,mode=0o700)
  job=home/'.hermes/.lifeos-releases'/('a'*32);job.mkdir(parents=True,mode=0o700)
  path=home/'.local/state/lifeos-hook-bridge/version-drift-baseline.json';path.parent.mkdir(parents=True,mode=0o700)
  baseline={'schema':2,'version':'7.40.4','created_at':m.PUBLICATION_TIME+100,'source_commit':catalog['source_commit'],'source_root':str(job/'package/lifeos/LifeOS/install'),'installed_root':str(installed),'files':catalog['files']}
  raw=(json.dumps(baseline)+'\n').encode();path.write_bytes(raw);path.chmod(0o600)
  intent=job/'mount-intent.json';value={'prior_journal_sha256':None,'action':'apply'};intent.write_text(json.dumps(value));intent.chmod(0o600);os.utime(intent,(m.PUBLICATION_TIME+101,m.PUBLICATION_TIME+101))
  entry={'target':str(path),'kind':'file','source':str(path)};entries=[entry];overrides={}
  if label=='missing-entry':entries=[]
  if label=='duplicate-entry':entries=[entry,dict(entry)]
  if label=='wrong-kind':entry['kind']='directory'
  if label=='wrong-source':entry['source']=str(home/'other.json')
  if label=='wrong-target':entry['target']=str(home/'other.json')
  if label=='current-mount-collision':overrides[str(path)]={'type':'file','mode':0o600,'sha256':hashlib.sha256(raw).hexdigest()}
  if label=='baseline-mode':path.chmod(0o644)
  if label=='intent-mode':intent.chmod(0o644)
  if label in ['baseline-symlink','intent-symlink']:
   selected=path if label.startswith('baseline') else intent;other=selected.with_name(selected.name+'.other');selected.rename(other);selected.symlink_to(other)
  if label in ['baseline-hardlink','intent-hardlink']:
   selected=path if label.startswith('baseline') else intent;os.link(selected,selected.with_name(selected.name+'.linked'))
  if label=='intent-action':value['action']='restore';intent.write_text(json.dumps(value))
  if label=='intent-extra-field':value['operation']='b'*32;intent.write_text(json.dumps(value))
  if label=='intent-malformed-prior':value['prior_journal_sha256']='wrong';intent.write_text(json.dumps(value))
  if label=='intent-too-large':intent.write_text(json.dumps(value)+' '*4096)
  if label=='intent-too-early':os.utime(intent,(m.PUBLICATION_TIME,m.PUBLICATION_TIME))
  original_proof=m.prove_baseline;original_uid=os.getuid;uid_calls=[]
  if label in ['baseline-owner','intent-owner']:
   def uid():
    uid_calls.append(True);wrong=(len(uid_calls)==1) if label=='baseline-owner' else (len(uid_calls)==2)
    return original_uid()+1 if wrong else original_uid()
   m.os.getuid=uid
  if label in ['baseline-changed-during-proof','intent-changed-during-proof']:
   def race(*args):
    result=original_proof(*args)
    if label.startswith('baseline'):path.write_bytes(raw+b' ')
    else:intent.write_text(json.dumps({'prior_journal_sha256':None,'action':'restore'}))
    return result
   m.prove_baseline=race
  accepted=True;error=None;returned=None
  try:returned=m.baseline_override(job,{'installed':str(installed)},SimpleNamespace(_load=lambda:{'entries':entries}),overrides)
  except (AssertionError,KeyError,ValueError,TypeError,OSError) as exc:accepted=False;error=type(exc).__name__
  finally:m.prove_baseline=original_proof;m.os.getuid=original_uid
  assert accepted==(label=='positive'),(label,error)
  if accepted:assert returned==(str(path),{'type':'file','mode':0o600,'sha256':hashlib.sha256(raw).hexdigest()})
  results.append({'case':label,'accepted':accepted,'error_type':error,'status':'PASS','uid_boundary_injected':label.endswith('-owner'),'fixture_files_only':True})
report={'status':'PASS','cases':results,'positive':1,'refusals':len(labels)-1,'remote_calls':False,'live_files_read':False,'guest_receipts_created':False}
(r/'outer-baseline-proof-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
