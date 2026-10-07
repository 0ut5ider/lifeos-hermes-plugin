# ABOUTME: Independently verifies raw version-drift effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from datetime import datetime

root=Path(__file__).resolve().parent
config=json.loads((root/'configuration.json').read_text())
assert (root/'run.done').read_text().strip()=='0'
public=root/'public'
public.mkdir(exist_ok=True)
sha=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
write=lambda path,data: path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
manifest=json.loads((root/'runtime-manifest.json').read_text())
staged=Path('/var/tmp/lifeos-paired-context-response-20261005')
mismatches=[name for name,value in manifest['source_sha256'].items() if not (staged/name).is_file() or sha(staged/name)!=value]
assert not mismatches,mismatches
runtime={'verified_source_files':len(manifest['source_sha256']),'source_mismatches':mismatches,
 'source_manifest_artifact':'../2026-10-05-paired-context-response/runtime-manifest.json',
 'native_cli_sha256':sha(Path(config['native']['command'][0])),
 'hermes_interpreter_sha256':sha(Path(config['hermes']['command'][0])),
 'trace_script_sha256':sha(Path(config['native']['trace_script'])),
 'candidate_sha256':{name:sha(root/name) for name in ('paired_lifecycle_effects.py','paired_response_server.py','configuration.json','run.py','collect.py')}}
native_root=Path(config['native']['hook_root'])
runtime['native_program_sha256']={str(path.relative_to(native_root)):sha(path)
 for folder in ('hooks','LIFEOS/TOOLS') for path in sorted((native_root/folder).rglob('*.ts')) if path.is_file()}
hermes_root=Path(config['hermes']['hook_root'])
runtime['selected_hook_sha256']={'native':sha(native_root/'hooks/VersionDrift.hook.ts'),'hermes':sha(hermes_root/'hooks/VersionDrift.hook.ts')}
write(public/'runtime-check.json',runtime)
for name in ('configuration.json','run.py','collect.py','run.done','run-output.txt'):
 shutil.copy2(root/name,public/name)
shutil.copy2(root/'paired_lifecycle_effects.py',public/'paired-lifecycle-driver.py')
shutil.copy2(root/'paired_response_server.py',public/'paired-response-server.py')
shutil.copy2(root/'results/paired-results.json',public/'paired-results.json')
paired=json.loads((public/'paired-results.json').read_text())
# case: changed files, tag present, tag age hours, version, prior nag, asynchronous, nag expected
expected={'version-drift-count':(10,True,0,'1.0.0',False,False,True),
 'version-drift-aged':(1,True,72,'1.0.0',False,False,True),
 'version-drift-below':(1,True,0,'1.0.0',False,False,False),
 'version-drift-bump':(10,True,0,'1.0.1',False,False,False),
 'version-drift-recent':(10,True,0,'1.0.0',True,False,False),
 'version-drift-untagged':(10,False,0,'1.0.0',False,False,False),
 'version-drift-async-count':(10,True,0,'1.0.0',False,True,True)}
assert [case['id'] for case in paired['cases']]==list(expected)
state_name='LIFEOS/MEMORY/STATE/version-drift-nag.json'
decode=lambda files,name: base64.b64decode(files[name]['content_base64']).decode()
proof=[]
for case in paired['cases']:
 assert not case['errors'],case
 case_id=case['id']
 changed,tagged,age,version,prior,asynchronous,nag=expected[case_id]
 for side in ('native','hermes'):
  home=Path(config[side]['home_root'])/'results'/case_id
  destination=public/side/case_id;destination.mkdir(parents=True,exist_ok=True)
  result=json.loads((home/'result.json').read_text())
  for artifact,value in result['raw_artifacts'].items():
   assert sha(home/artifact)==value,(side,case_id,artifact)
   shutil.copy2(home/artifact,destination/artifact)
  for artifact in ('result.json','clock-bounds.json'):
   shutil.copy2(home/artifact,destination/artifact)
  events=[json.loads(line) for line in (home/'fixture-events.jsonl').read_text().splitlines()]
  assert [row['hook_event_name'] for row in events]==['SessionStart','UserPromptSubmit','SessionEnd']
  assert len({row['session_id'] for row in events})==1
  hooks=[json.loads(line) for line in (home/'hooks.jsonl').read_text().splitlines()]
  assert len(hooks)==1 and hooks[0]['id']=='UserPromptSubmit.4.1' and hooks[0]['exit_code']==0
  payload=json.loads(base64.b64decode(hooks[0]['stdin_base64']))
  assert payload['prompt']=='Reply with READY.' and payload['session_id']==result['session_id']
  before=json.loads((home/'fixture-files-before.json').read_text())
  after=json.loads((home/'fixture-files-after.json').read_text())
  core=[name for name in before if name.startswith('hooks/core-')]
  assert len(core)==10
  assert sum(decode(before,name)=='Changed core content\n' for name in core)==changed
  assert decode(before,'LIFEOS/VERSION').strip()==version
  assert (state_name in before)==prior
  assert all(after.get(name)==value for name,value in before.items() if name!=state_name)
  repository=home/'.claude/.git'
  tags=sorted(path.name for path in (repository/'refs/tags').iterdir())
  assert tags==(['v1.0.0'] if tagged else [])
  settings=json.loads(decode(before,'settings.json'))
  selected=[hook for group in settings['hooks']['UserPromptSubmit'] for hook in group['hooks'] if 'UserPromptSubmit.4.1' in hook['command']]
  assert len(selected)==1 and selected[0].get('async',False)==asynchronous
  assert selected[0]['timeout']==(10 if asynchronous else 30)
  bounds=json.loads((home/'clock-bounds.json').read_text())
  output=hooks[0]['stdout']
  line=''
  if nag:
   line=json.loads(output)['hookSpecificOutput']['additionalContext']
   label=f' (tag {age}h old)' if age else ''
   assert line.startswith(f'⏫ VERSION-DRIFT: {changed} core file(s) ahead of v1.0.0{label}, no bump in flight ')
   assert line.endswith('or defer explicitly to the principal.')
   state=json.loads(decode(after,state_name))
   assert (state['count'],state['tag'])==(changed,'v1.0.0')
   written=datetime.fromisoformat(state['ts'].replace('Z','+00:00'))
   assert datetime.fromisoformat(bounds['started_at']).replace(microsecond=0)<=written<=datetime.fromisoformat(bounds['finished_at'])
  else:
   assert output==''
   assert (state_name in after)==prior
   if prior:
    assert after[state_name]==before[state_name]
    assert json.loads(decode(after,state_name))['tag']=='v0.9.0'
  cli=[]
  for text in (home/'cli.log').read_text().splitlines():
   try:row=json.loads(text)
   except ValueError:continue
   if isinstance(row,dict) and row.get('type')=='result':cli.append(row)
  assert len(cli)==1
  response=cli[0].get('result' if side=='native' else 'text','')
  assert response.strip()
  requests=json.loads((home/'requests-private.json').read_text())
  assert (home/'requests-private.json').stat().st_mode & 0o777==0o600
  generation=[row for row in requests if row['path'].startswith('/v1/')]
  assert len(generation)==1 and generation[0]['upstream_status']==200
  row=generation[0]
  for key in ('body','response_body'):
   assert hashlib.sha256(base64.b64decode(row[key+'_base64'])).hexdigest()==row[key+'_sha256']
  for definition in result['hook_definitions']:
   for path,value in definition['source_files'].items():assert sha(Path(path))==value
  model_text=json.dumps(json.loads(base64.b64decode(row['body_base64'])),ensure_ascii=False)
  present=bool(line and line in model_text)
  assert 'VERSION-DRIFT' not in model_text or present
  assert present==(nag and not asynchronous)
  proof.append({'case':case_id,'side':side,'session_id':result['session_id'],
   'changed_core_files':changed,'tags':tags,'tag_age_hours':age,'version':version,
   'prior_nag_present':prior,'asynchronous':asynchronous,'nag_line':line,
   'clock_bounds':bounds,'worktree_preserved':True,'model_nag_present':present,
   'user_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
   'request_sha256':row['body_sha256'],'response_sha256':row['response_body_sha256'],
   'actual_model':row['actual_model'],'upstream_status':row['upstream_status']})
write(public/'drift-proof.json',proof)
with tarfile.open(root/'public.tar.gz','w:gz') as archive:
 archive.add(public,arcname='paired-version-drift')
print(json.dumps({'verified_clients':len(proof),'verified_source_files':len(manifest['source_sha256']),
 'native_programs':len(runtime['native_program_sha256']),'archive':str(root/'public.tar.gz')}))
