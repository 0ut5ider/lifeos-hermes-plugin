# ABOUTME: Independently verifies raw tool logging effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from datetime import datetime

SELECTED=('hooks/EventLogger.hook.ts','hooks/LoopDetector.hook.ts')

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
commands={'tool-log-success':"printf 'PAIR_%s' TOOL_LOG",'tool-log-repeat':"printf 'PAIR_%s' TOOL_LOG",'tool-log-failure':'ls pair-missing-tool-log'}
selected={'tool-log-success':['PostToolUse.11.1','PostToolUse.12.2'],'tool-log-repeat':['PostToolUse.12.2'],
 'tool-log-failure':['PostToolUseFailure.1.1','PostToolUseFailure.3.1']}
alert="[LOOP DETECTED] You've called Bash 3 times with the same input this session without progress."
paired=json.loads((public/'paired-results.json').read_text())
assert [case['id'] for case in paired['cases']]==list(commands)
proof=[]
for case in paired['cases']:
 assert not case['errors'],case
 name=case['id'];failure=name=='tool-log-failure';repeat=name=='tool-log-repeat'
 for side in ('native','hermes'):
  data=client(name,side)
  session=data['result']['session_id']
  calls=len(data['hooks'])//len(selected[name])
  assert calls>=(3 if repeat else 1) and (repeat or calls==1)
  assert sorted({row['id'] for row in data['hooks']})==sorted(selected[name])
  assert all(row['exit_code']==0 for row in data['hooks'])
  required=[payload for payload in data['payloads']][:(3 if repeat else 1)*len(selected[name])]
  for payload in required:
   assert payload['hook_event_name']==('PostToolUseFailure' if failure else 'PostToolUse')
   assert payload['tool_name']=='Bash' and payload['tool_input']['command']==commands[name]
   assert payload['session_id']==session
  settings=json.loads(decode(data['before'],'settings.json'))
  group,=settings['hooks']['PostToolUseFailure' if failure else 'PostToolUse']
  assert 'matcher' not in group
  if name=='tool-log-success':
   assert [(hook.get('async',False),hook['timeout']) for hook in group['hooks']]==[(True,5),(False,30)]
  files=data['after']
  activity_name='LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
  failure_name='LIFEOS/MEMORY/OBSERVABILITY/tool-failures.jsonl'
  assert (activity_name in files)==(name=='tool-log-success') and (failure_name in files)==failure
  if name=='tool-log-success':
   row,=[json.loads(line) for line in decode(files,activity_name).splitlines()]
   assert (row['event'],row['tool_name'],row['session_id'])==('tool_use','Bash',session)
   assert json.loads(row['tool_input_preview'])['command']==commands[name]
   assert row['ground_truth']['command']==commands[name]
   # Accepted host difference: Claude Code gives separate streams; Hermes gives one combined stream and an exit code.
   expected_fields={'command','stdout_preview','stdout_bytes','stderr_preview'} if side=='native' else {'command','combined_output_preview','combined_output_bytes','exit_code'}
   assert set(row['ground_truth'])==expected_fields,sorted(row['ground_truth'])
   assert row['ground_truth']['stdout_preview' if side=='native' else 'combined_output_preview']=='PAIR_TOOL_LOG'
   assert set(json.loads(row['tool_input_preview']))==({'command','description'} if side=='native' else {'command'})
  if failure:
   row,=[json.loads(line) for line in decode(files,failure_name).splitlines()]
   assert (row['event'],row['tool_name'],row['session_id'])==('tool_failure','Bash',session)
   assert json.loads(row['tool_input_preview'])['command']==commands[name]
   assert row['error']=="Exit code 2\nls: cannot access 'pair-missing-tool-log': No such file or directory",row['error']
   assert set(json.loads(row['tool_input_preview']))==({'command','description'} if side=='native' else {'command'})
  state=json.loads(decode(files,'LIFEOS/MEMORY/STATE/loop-detector/'+session+'.json'))
  assert state['seq']==calls and len(state['window'])==calls
  assert all(entry['tool']=='Bash' and entry['failed']==failure for entry in state['window'][:3])
  loop_rows=[row for row in data['hooks'] if row['id']==selected[name][-1]]
  positions=[index for index,row in enumerate(loop_rows,1) if alert in row['stdout']]
  assert positions==([3] if repeat else []) and state['lastAlert']==(3 if repeat else 0)
  assert len(state['alerted'])==int(repeat)
  later=json.dumps([json.loads(base64.b64decode(row['body_base64'])) for row in data['generation'][1:]],ensure_ascii=False)
  assert (alert in later)==repeat and ('PAIR_TOOL_LOG' in later)==(not failure)
  assert len(data['generation'])>=2 and 'READY' in data['response']
  proof.append({**data['summary'],'command':commands[name],'tool_calls':calls,'loop_alert_positions':positions,
   'loop_alert_in_later_request':repeat,'activity_row':name=='tool-log-success','failure_row':failure,
   'loop_entries_failed':failure})
shutil.copy2(staged/'runtime-manifest.json',public/'runtime-manifest.json')
finish(proof,'tool-log-proof.json','paired-tool-failure-text')
