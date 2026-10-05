# ABOUTME: Independently verifies raw current-time effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

root=Path(__file__).resolve().parent
config=json.loads((root/'configuration.json').read_text())
assert (root/'run.done').read_text().strip()=='0'
public=root/'public'
public.mkdir(exist_ok=True)
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
for case in paired['cases']:
 assert not case['errors'],case
 case_id=case['id']
 zone='PAIR_INVALID_ZONE' if case_id=='time-context-invalid-zone' else 'America/Toronto' if case_id=='time-context-sync-toronto' else 'UTC'
 asynchronous=case_id=='time-context-async-utc'
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
  assert len(hooks)==1 and hooks[0]['id']=='UserPromptSubmit.8.1' and hooks[0]['exit_code']==0
  payload=json.loads(base64.b64decode(hooks[0]['stdin_base64']))
  assert payload['prompt']=='Reply with READY.' and payload['session_id']==result['session_id']
  before=json.loads((home/'fixture-files-before.json').read_text())
  after=json.loads((home/'fixture-files-after.json').read_text())
  assert before['settings.json']==after['settings.json']
  settings=json.loads(base64.b64decode(before['settings.json']['content_base64']))
  assert settings['principal']['timezone']==zone
  selected=[hook for group in settings['hooks']['UserPromptSubmit'] for hook in group['hooks'] if 'UserPromptSubmit.8.1' in hook['command']]
  assert len(selected)==1
  assert selected[0].get('async',False)==asynchronous
  if asynchronous:assert selected[0]['timeout']==5
  output=hooks[0]['stdout']
  bounds=json.loads((home/'clock-bounds.json').read_text())
  if zone=='PAIR_INVALID_ZONE':
   assert output==''
   clock_line=''
  else:
   match=re.search(r'Current time: ([A-Za-z]{3}) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ([A-Z]+) \(([^)]+)\)',output)
   assert match,output
   observed=datetime.strptime(match[2],'%Y-%m-%d %H:%M').replace(tzinfo=ZoneInfo(zone))
   part=('late night' if observed.hour<5 else 'early morning' if observed.hour<9 else 'morning' if observed.hour<12 else 'afternoon' if observed.hour<17 else 'evening' if observed.hour<21 else 'late night')
   assert (match[1],match[3],match[4])==(observed.strftime('%a'),observed.tzname(),part)
   start=datetime.fromisoformat(bounds['started_at']).replace(second=0,microsecond=0)
   end=datetime.fromisoformat(bounds['finished_at']).replace(second=0,microsecond=0)
   assert start<=observed.astimezone(timezone.utc)<=end
   assert '<time-now>' in output and '</time-now>' in output
   clock_line=match[0]
  cli=[]
  for line in (home/'cli.log').read_text().splitlines():
   try:row=json.loads(line)
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
  request=json.loads(base64.b64decode(row['body_base64']))
  model_text=json.dumps(request,ensure_ascii=False)
  present=bool(clock_line and clock_line in model_text and '<time-now>' in model_text)
  assert present==(zone!='PAIR_INVALID_ZONE' and not asynchronous)
  proof.append({'case':case_id,'side':side,'session_id':result['session_id'],
   'timezone':zone,'asynchronous':asynchronous,'clock_line':clock_line,
   'clock_bounds':bounds,'clock_bounds_sha256':sha(home/'clock-bounds.json'),
   'settings_preserved':True,'model_clock_present':present,
   'user_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
   'request_sha256':row['body_sha256'],'response_sha256':row['response_body_sha256'],
   'actual_model':row['actual_model'],'upstream_status':row['upstream_status']})
write(public/'clock-proof.json',proof)
with tarfile.open(root/'public.tar.gz','w:gz') as archive:
 archive.add(public,arcname='paired-time-context')
print(json.dumps({'verified_clients':len(proof),'verified_source_files':len(manifest['source_sha256']),
 'native_programs':len(runtime['native_program_sha256']),'archive':str(root/'public.tar.gz')}))
