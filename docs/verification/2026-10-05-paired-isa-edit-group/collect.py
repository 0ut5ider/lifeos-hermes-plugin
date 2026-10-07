# ABOUTME: Independently verifies raw ISA edit group effects before exporting public evidence.
# ABOUTME: Keeps full model request and response bodies private outside the Git repository.
import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from datetime import datetime

SELECTED=tuple('hooks/'+n+'.hook.ts' for n in ('ISASync','ISAStaleWriteGuard','CheckpointPerISC','ConfigEvalFire','AtlasEventCapture','KnowledgeWriteGuard','ComplexityRatchet'))

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
import subprocess
paired=json.loads((public/'paired-results.json').read_text())
case,=paired['cases']
assert case['id']=='isa-edit-close' and not case['errors'],case
ids=[f'PostToolUse.9.{i}' for i in range(1,8)]
text='ISC-1 (pair-run): Paired criterion closes'
proof=[]
for side in ('native','hermes'):
 data=client('isa-edit-close',side)
 work=data['home']/'.claude/LIFEOS/MEMORY/WORK/pair-run'
 target=work/'ISA.md'
 calls=len(data['hooks'])//7
 assert calls>=1 and sorted(r['id'] for r in data['hooks'])==sorted(ids*calls)
 assert all(r['exit_code']==0 for r in data['hooks'])
 for p in data['payloads']:
  assert p['hook_event_name']=='PostToolUse' and p['tool_name']=='Edit' and p['tool_input']['file_path']==str(target)
 content=target.read_text()
 assert '- [x] ISC-1: Paired criterion closes' in content and '- [ ] ISC-1' not in content
 shutil.copy2(target,data['destination']/'ISA.md')
 git=lambda *a: subprocess.run(['git','-C',str(data['home']/'checkpoint-repo'),'-c','safe.directory=*',*a],capture_output=True,text=True,check=True).stdout
 subject,body=git('log','-1','--format=%s'),git('log','-1','--format=%b').strip()
 if side=='native': assert subject.strip()==text and body==''
 else: assert subject.strip()=='chore(checkpoint): ISC-1 (pair-run): Paired crite' and body==text
 assert git('show','--name-only','--format=','HEAD').split()==['tracked.txt'] and git('status','--porcelain').strip()==''
 strip=[json.loads(r['stdout'])['hookSpecificOutput']['additionalContext'] for r in data['hooks'] if r['id']=='PostToolUse.9.1'][0]
 assert strip.startswith('<lifeos-ascent-delta>') and strip.endswith('</lifeos-ascent-delta>')
 later=json.dumps([json.loads(base64.b64decode(r['body_base64'])) for r in data['generation'][1:]],ensure_ascii=False)
 delivered='lifeos-ascent-delta' in later
 views=json.loads(decode(data['after'],'LIFEOS/MEMORY/STATE/isa-session-view/'+data['result']['session_id']+'.json'))['views']
 assert views[str(target)]==hashlib.sha256(content.encode()).hexdigest()
 proof.append({**data['summary'],'edit_calls':calls,'checkpoint_subject':subject.strip(),'checkpoint_body':body,
  'strip_line':[l for l in strip.splitlines() if l.startswith('════')][0],'strip_in_later_request':delivered,
  'isa_sha256':sha(target),'view_matches_content':True})
assert proof[0]['strip_line']==proof[1]['strip_line'] and proof[0]['strip_in_later_request']==proof[1]['strip_in_later_request']
finish(proof,'isa-edit-proof.json','paired-isa-edit-group')
