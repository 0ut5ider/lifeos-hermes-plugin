# ABOUTME: Independently verifies raw mutation hint effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from datetime import datetime

SELECTED=('hooks/AtlasEventCapture.hook.ts',)

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
runtime['selected_hook_sha256']={name:{'native':sha(native_root/name),'hermes':sha(hermes_root/name)} for name in SELECTED}
write(public/'runtime-check.json',runtime)
for name in ('configuration.json','run.py','collect.py','run.done','run-output.txt'):
 shutil.copy2(root/name,public/name)
shutil.copy2(root/'paired_lifecycle_effects.py',public/'paired-lifecycle-driver.py')
shutil.copy2(root/'paired_response_server.py',public/'paired-response-server.py')
shutil.copy2(root/'results/paired-results.json',public/'paired-results.json')
paired=json.loads((public/'paired-results.json').read_text())

def client(case_id,side,event_names=('SessionStart','UserPromptSubmit','SessionEnd')):
 home=Path(config[side]['home_root'])/'results'/case_id
 destination=public/side/case_id;destination.mkdir(parents=True,exist_ok=True)
 result=json.loads((home/'result.json').read_text())
 for artifact,value in result['raw_artifacts'].items():
  assert sha(home/artifact)==value,(side,case_id,artifact)
  shutil.copy2(home/artifact,destination/artifact)
 for artifact in ('result.json','clock-bounds.json'):
  if (home/artifact).is_file():shutil.copy2(home/artifact,destination/artifact)
 events=[json.loads(line) for line in (home/'fixture-events.jsonl').read_text().splitlines()]
 assert [row['hook_event_name'] for row in events]==list(event_names)
 assert {row['session_id'] for row in events}=={result['session_id']}
 hooks=[json.loads(line) for line in (home/'hooks.jsonl').read_text().splitlines()]
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
 for row in generation:
  assert row['upstream_status']==200
  for key in ('body','response_body'):
   assert hashlib.sha256(base64.b64decode(row[key+'_base64'])).hexdigest()==row[key+'_sha256']
 for definition in result['hook_definitions']:
  for path,value in definition['source_files'].items():assert sha(Path(path))==value
 before=json.loads((home/'fixture-files-before.json').read_text())
 after=json.loads((home/'fixture-files-after.json').read_text())
 return {'home':home,'destination':destination,'result':result,'hooks':hooks,'response':response,
  'generation':generation,'before':before,'after':after,
  'payloads':[json.loads(base64.b64decode(row['stdin_base64'])) for row in hooks],
  'summary':{'case':case_id,'side':side,'session_id':result['session_id'],
   'user_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
   'request_sha256':[row['body_sha256'] for row in generation],
   'response_sha256':[row['response_body_sha256'] for row in generation],
   'actual_model':sorted({row['actual_model'] for row in generation}),'upstream_status':[row['upstream_status'] for row in generation]}}
decode=lambda files,name: base64.b64decode(files[name]['content_base64']).decode()

def finish(proof,name,archive):
 write(public/name,proof)
 with tarfile.open(root/'public.tar.gz','w:gz') as stream:
  stream.add(public,arcname=archive)
 print(json.dumps({'verified_clients':len(proof),'verified_source_files':len(manifest['source_sha256']),
  'native_programs':len(runtime['native_program_sha256']),'archive':str(root/'public.tar.gz')}))
commands={'atlas-bash-systemd':"printf 'PAIR_ATLAS systemctl --user daemon-reload'",
 'atlas-bash-plain':"printf 'PAIR_ATLAS plain command'",
 'atlas-bash-multiple':"printf 'PAIR_ATLAS gh repo create fixture; launchctl load fixture'"}
sources={'atlas-bash-systemd':['systemd'],'atlas-bash-plain':[],'atlas-bash-multiple':['github','launchd']}
paired=json.loads((public/'paired-results.json').read_text())
assert [case['id'] for case in paired['cases']]==list(commands)
prior={'ts':'2026-10-01T00:00:00.000Z','source':'projects','tool':'Write'}
proof=[]
for case in paired['cases']:
 assert not case['errors'],case
 for side in ('native','hermes'):
  data=client(case['id'],side)
  assert [row['id'] for row in data['hooks']]==['PostToolUse.13.1'] and data['hooks'][0]['exit_code']==0
  assert data['hooks'][0]['stdout']==''
  payload,=data['payloads']
  assert payload['hook_event_name']=='PostToolUse' and payload['tool_name']=='Bash'
  assert payload['tool_input']['command']==commands[case['id']]
  assert payload['session_id']==data['result']['session_id']
  settings=json.loads(decode(data['before'],'settings.json'))
  group,=settings['hooks']['PostToolUse']
  assert group['matcher']=='Bash' and len(group['hooks'])==1
  events=data['home']/'.local/state/lifeos/atlas/events.jsonl'
  shutil.copy2(events,data['destination']/'atlas-events.jsonl')
  rows=[json.loads(line) for line in events.read_text().splitlines()]
  assert rows[0]==prior
  bounds=json.loads((data['home']/'clock-bounds.json').read_text())
  assert [(row['source'],row['tool']) for row in rows[1:]]==[(source,'Bash') for source in sources[case['id']]]
  for row in rows[1:]:
   written=datetime.fromisoformat(row['ts'].replace('Z','+00:00'))
   assert datetime.fromisoformat(bounds['started_at']).replace(microsecond=0)<=written<=datetime.fromisoformat(bounds['finished_at'])
  assert len(data['generation'])==2 and 'READY' in data['response']
  assert 'PAIR_ATLAS' in json.dumps(payload.get('tool_response',''))
  proof.append({**data['summary'],'command':commands[case['id']],'hint_sources':sources[case['id']],
   'prior_event_preserved':True,'tool_output_contains_marker':True,
   'events_sha256':sha(events)})
finish(proof,'hint-proof.json','paired-atlas-hints')
