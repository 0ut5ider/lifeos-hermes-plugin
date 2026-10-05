# ABOUTME: Independently verifies raw feedback effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

root=Path(__file__).resolve().parent
config=json.loads((root/'configuration.json').read_text())
assert (root/'run.done').read_text().strip()=='0'
public=root/'public-v2'
public.mkdir()
sha=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
write=lambda path,data: path.write_text(json.dumps(data,indent=2)+'\n')
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
write(public/'runtime-check.json',runtime)
for name in ('configuration.json','run.py','collect.py','run.done','run-output.txt'):
 shutil.copy2(root/name,public/name)
shutil.copy2(root/'paired_lifecycle_effects.py',public/'paired-lifecycle-driver.py')
shutil.copy2(root/'paired_response_server.py',public/'paired-response-server.py')
shutil.copy2(root/'results/paired-results.json',public/'paired-results.json')
paired=json.loads((public/'paired-results.json').read_text())
proof=[]
prompts={'feedback-rating':'8 great result','feedback-bare-rating':'10','feedback-praise':'great job',
 'feedback-neutral':'2 of the files were inspected','feedback-low-rating':'4 needs clearer details'}
cache_expected='PAIR_FEEDBACK_RESPONSE\n'+'Synthetic prior response context. '*24
for case in paired['cases']:
 assert not case['errors'],case
 for side in ('native','hermes'):
  home=Path(config[side]['home_root'])/'results'/case['id']
  destination=public/side/case['id'];destination.mkdir(parents=True)
  result=json.loads((home/'result.json').read_text())
  for name,value in result['raw_artifacts'].items():
   assert sha(home/name)==value,(side,case['id'],name)
   shutil.copy2(home/name,destination/name)
  shutil.copy2(home/'result.json',destination/'result.json')
  events=[json.loads(line) for line in (home/'fixture-events.jsonl').read_text().splitlines()]
  assert [row['hook_event_name'] for row in events]==['SessionStart','UserPromptSubmit','SessionEnd']
  assert len({row['session_id'] for row in events})==1
  assert events[1]['prompt']==prompts[case['id']]
  hooks=[json.loads(line) for line in (home/'hooks.jsonl').read_text().splitlines()]
  assert len(hooks)==1 and hooks[0]['id']=='UserPromptSubmit.2.1' and hooks[0]['exit_code']==0
  payload=json.loads(base64.b64decode(hooks[0]['stdin_base64']))
  assert payload['prompt']==prompts[case['id']] and payload['session_id']==result['session_id']
  files=json.loads((home/'fixture-files-after.json').read_text())
  content=lambda name:base64.b64decode(files[name]['content_base64']).decode()
  assert content('LIFEOS/MEMORY/STATE/last-response.txt')==cache_expected
  ratings=[json.loads(line) for line in content('LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl').splitlines()]
  before=json.loads((home/'fixture-files-before.json').read_text())
  original=json.loads(base64.b64decode(before['LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl']['content_base64']))
  assert ratings[0]==original
  assert len(ratings)==(1 if case['id']=='feedback-neutral' else 2)
  if len(ratings)==2:
   assert ratings[1]['session_id']==result['session_id']
   assert ratings[1]['response_preview']==cache_expected[:500]
   assert ratings[1]['rating']=={'feedback-rating':8,'feedback-bare-rating':10,'feedback-praise':8,'feedback-low-rating':4}[case['id']]
   assert ratings[1]['source']==('implicit' if case['id']=='feedback-praise' else 'explicit')
  learning=[name for name in files if '_LEARNING_' in name and name.endswith('.md')]
  assert len(learning)==int(case['id']=='feedback-low-rating')
  if learning:
   text=content(learning[0])
   assert cache_expected in text and '**Feedback:** needs clearer details' in text and 'rated 4/10 by FixtureOwner.' in text
  cli=[]
  for line in (home/'cli.log').read_text().splitlines():
   try: row=json.loads(line)
   except ValueError: continue
   if isinstance(row,dict) and row.get('type')=='result':cli.append(row)
  assert len(cli)==1
  response=cli[0].get('result' if side=='native' else 'text','')
  assert response.strip(), 'The final client response is empty'
  requests=json.loads((home/'requests-private.json').read_text())
  assert (home/'requests-private.json').stat().st_mode & 0o777==0o600
  generation=[row for row in requests if row['path'].startswith('/v1/')]
  assert len(generation)==1 and generation[0]['upstream_status']==200
  row=generation[0]
  assert hashlib.sha256(base64.b64decode(row['body_base64'])).hexdigest()==row['body_sha256']
  assert hashlib.sha256(base64.b64decode(row['response_body_base64'])).hexdigest()==row['response_body_sha256']
  for definition in result['hook_definitions']:
   for path,value in definition['source_files'].items():assert sha(Path(path))==value
  proof.append({'case':case['id'],'side':side,'prompt':payload['prompt'],
   'session_id':result['session_id'],'prior_rating_preserved':True,'rating_count':len(ratings),
   'cache_sha256':hashlib.sha256(cache_expected.encode()).hexdigest(),'learning_paths':learning,
   'user_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
   'request_sha256':row['body_sha256'],'response_sha256':row['response_body_sha256'],
   'actual_model':row['actual_model'],'upstream_status':row['upstream_status']})
write(public/'feedback-proof.json',proof)
failed=public/'failed-blocked-observer';failed.mkdir()
old=Path('/var/tmp/lifeos-paired-feedback-20261005')
for name in ('run.done','run-output.txt','configuration.json','run.py'):
 shutil.copy2(old/name,failed/name)
shutil.copy2(old/'paired_lifecycle_effects.py',failed/'paired-lifecycle-driver.py')
oldhome=Path('/home/lifeos-claude-ref/workspace/paired-feedback-20261005/results/feedback-rating')
for name in ('cli.log','fixture-events.jsonl','before-state.json','fixture-files-before.json'):
 shutil.copy2(oldhome/name,failed/name)
old=Path('/var/tmp/lifeos-paired-feedback-v2-20261005')
failed=public/'failed-unconstrained-response';failed.mkdir()
for name in ('run.done','run-output.txt','configuration.json'):
 shutil.copy2(old/name,failed/name)
shutil.copy2(old/'results/paired-results.json',failed/'paired-results.json')
with tarfile.open(root/'public.tar.gz','w:gz') as archive:
 archive.add(public,arcname='paired-feedback')
print(json.dumps({'verified_clients':len(proof),'verified_source_files':len(manifest['source_sha256']),
 'native_programs':len(runtime['native_program_sha256']),'archive':str(root/'public.tar.gz')}))
