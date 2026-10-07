# ABOUTME: Independently verifies raw evaluation trigger effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from datetime import datetime

SELECTED=('hooks/AtlasEventCapture.hook.ts','hooks/ConfigEvalFire.hook.ts')

root=Path(__file__).resolve().parent
config=json.loads((root/'configuration.json').read_text())
assert (root/'run.done').read_text().strip()=='0'
public=root/'public'
public.mkdir(exist_ok=True)
sha=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
write=lambda path,data: path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
manifest=json.loads((root/'runtime-manifest.json').read_text())
staged=Path('/var/tmp/lifeos-paired-runtime-20261005b')
mismatches=[name for name,value in manifest['source_sha256'].items() if not (staged/name).is_file() or sha(staged/name)!=value]
assert not mismatches,mismatches
runtime={'verified_source_files':len(manifest['source_sha256']),'source_mismatches':mismatches,
 'source_manifest_artifact':'../2026-10-05-paired-tool-failure-text/runtime-manifest.json','plugin_commit':manifest['plugin_commit'],
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
shapes={'file-hint-sentinel-debounced':('Write','example.hook.ts',[],'8'),'file-hint-sentinel-no-runner':('Write','example.hook.ts',[],'8')}
seeded={'file-hint-sentinel-debounced'}
seed='First fixture line\nPAIR_OLD_LINE\nLast fixture line\n'
prior={'ts':'2026-10-01T00:00:00.000Z','source':'projects','tool':'Write'}
paired=json.loads((public/'paired-results.json').read_text())
assert [case['id'] for case in paired['cases']]==list(shapes)
proof=[]
for case in paired['cases']:
 assert not case['errors'],case
 name=case['id'];tool,file_name,sources,group_number=shapes[name]
 identifiers=[f'PostToolUse.{group_number}.5',f'PostToolUse.{group_number}.4']
 for side in ('native','hermes'):
  data=client(name,side)
  target=data['home']/'project'/file_name
  calls=len(data['hooks'])//2
  assert calls>=1 and sorted(row['id'] for row in data['hooks'])==sorted(identifiers*calls)
  assert all(row['exit_code']==0 and row['stdout']=='' for row in data['hooks'])
  for payload in data['payloads']:
   assert payload['hook_event_name']=='PostToolUse' and payload['tool_name']==tool
   assert payload['tool_input']['file_path']==str(target) and payload['session_id']==data['result']['session_id']
  settings=json.loads(decode(data['before'],'settings.json'))
  group,=settings['hooks']['PostToolUse']
  assert group['matcher']==tool and len(group['hooks'])==2
  shutil.copy2(target,data['destination']/('target-'+file_name))
  content=target.read_text()
  assert content.strip()==('PAIR_FILE_CONTENT' if tool=='Write' else seed.replace('PAIR_OLD_LINE','PAIR_NEW_LINE').strip())
  events=data['home']/'.local/state/lifeos/atlas/events.jsonl'
  shutil.copy2(events,data['destination']/'atlas-events.jsonl')
  rows=[json.loads(line) for line in events.read_text().splitlines()]
  bounds=json.loads((data['home']/'clock-bounds.json').read_text())
  assert rows[0]==prior and [(row['source'],row['tool']) for row in rows[1:]]==[(source,tool) for source in sources]*calls
  for row in rows[1:]:
   written=datetime.fromisoformat(row['ts'].replace('Z','+00:00'))
   assert datetime.fromisoformat(bounds['started_at']).replace(microsecond=0)<=written<=datetime.fromisoformat(bounds['finished_at'])
  state='LIFEOS/MEMORY/OBSERVABILITY/config-eval-state.json'
  assert (state in data['before'])==(name in seeded) and data['after'].get(state)==data['before'].get(state)
  assert not (data['home']/'.claude/LIFEOS/TOOLS/ConfigEvalOnChange.ts').exists()
  assert len(data['generation'])>=2
  proof.append({**data['summary'],'tool':tool,'file':file_name,'tool_calls':calls,'hint_sources':sources,
   'hint_rows':len(rows)-1,'target_sha256':sha(target),'evaluation_state_seeded':name in seeded,'evaluation_state_unchanged':True,'runner_present':False})
finish(proof,'config-eval-proof.json','paired-config-eval')
