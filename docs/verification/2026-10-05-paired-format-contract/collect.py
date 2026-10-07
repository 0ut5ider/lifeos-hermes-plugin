# ABOUTME: Independently verifies raw format reminder effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import time

root=Path(__file__).resolve().parent
config=json.loads((root/'configuration.json').read_text())
assert (root/'run.done').read_text().strip()=='0'
public=root/'public'
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
clean='════ LifeOS ════\nFixture response.\n🗣️ Done.'
broken='delve '+chr(0x2014)*3+'\n'+''.join(f'Line {index}.\n' for index in range(16))
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
  prompt='Give a detailed report.' if case['id']=='format-contract-depth' else 'Reply with READY.'
  assert events[1]['prompt']==prompt
  hooks=[json.loads(line) for line in (home/'hooks.jsonl').read_text().splitlines()]
  assert len(hooks)==1 and hooks[0]['id']=='UserPromptSubmit.6.1' and hooks[0]['exit_code']==0
  payload=json.loads(base64.b64decode(hooks[0]['stdin_base64']))
  assert payload['prompt']==prompt and payload['session_id']==result['session_id']
  files=json.loads((home/'fixture-files-after.json').read_text())
  content=lambda name:base64.b64decode(files[name]['content_base64']).decode()
  name=case['id']
  initial=name=='format-contract-empty'
  cache_path='LIFEOS/MEMORY/STATE/last-response.txt'
  expected_cache=clean if name=='format-contract-clean' else broken
  if initial:
   assert cache_path not in files
  else:
   assert content(cache_path)==expected_cache
   before=json.loads((home/'fixture-files-before.json').read_text())
   assert files[cache_path]==before[cache_path]
   cache_age=time.time()-(home/'.claude'/cache_path).stat().st_mtime
   assert (cache_age>1800)==(name=='format-contract-stale')
  budget='depth requested, line cap lifted' if name=='format-contract-depth' else 'max 15 prose lines'
  previous=''
  if name=='format-contract-clean':previous=' Last response was clean (3 lines).'
  if name in {'format-contract-depth','format-contract-violations'}:
   previous=" Last response broke: no banner, no closer, 3 em-dashes, banned word 'delve'"
   previous+=', 17 lines (cap 15).' if name=='format-contract-violations' else '.'
  contract='FORMAT CONTRACT (check before writing, not after): '+budget+'; banner first, 🗣️ closer last, max 2 em-dashes.'+previous
  state=json.loads(content('LIFEOS/MEMORY/STATE/drift-reminder.json'))
  assert state=={'last_fired_turn':1 if initial else 7,'turn_count':1 if initial else 7,'last_text':contract,'schema_version':1}
  hook_output=json.loads(hooks[0]['stdout'])
  assert hook_output=={'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':contract}}
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
  request=json.loads(base64.b64decode(row['body_base64']))
  assert contract in json.dumps(request,ensure_ascii=False)
  proof.append({'case':name,'side':side,'prompt':payload['prompt'],
   'session_id':result['session_id'],'contract':contract,'turn_count':state['turn_count'],
   'last_fired_turn':state['last_fired_turn'],'cache_preserved':True,
   'cached_response_is_stale':name=='format-contract-stale','model_contract_present':True,
   'user_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
   'request_sha256':row['body_sha256'],'response_sha256':row['response_body_sha256'],
   'actual_model':row['actual_model'],'upstream_status':row['upstream_status']})
write(public/'format-proof.json',proof)
with tarfile.open(root/'public.tar.gz','w:gz') as archive:
 archive.add(public,arcname='paired-format-contract')
print(json.dumps({'verified_clients':len(proof),'verified_source_files':len(manifest['source_sha256']),
 'native_programs':len(runtime['native_program_sha256']),'archive':str(root/'public.tar.gz')}))
