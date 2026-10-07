# ABOUTME: Independently verifies raw end-of-turn render effects before exporting public evidence.
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
runtime['renderer_sha256']={'native':sha(native_root/'LIFEOS/TOOLS/ISARender.ts'),'hermes':sha(Path(config['hermes']['hook_root'])/'LIFEOS/TOOLS/ISARender.ts')}
runtime['selected_hook_sha256']={'native':sha(native_root/'hooks/ISARenderOnStop.hook.ts'),'hermes':sha(hermes_root/'hooks/ISARenderOnStop.hook.ts')}
write(public/'runtime-check.json',runtime)
for name in ('configuration.json','run.py','collect.py','run.done','run-output.txt'):
 shutil.copy2(root/name,public/name)
shutil.copy2(root/'paired_lifecycle_effects.py',public/'paired-lifecycle-driver.py')
shutil.copy2(root/'paired_response_server.py',public/'paired-response-server.py')
shutil.copy2(root/'results/paired-results.json',public/'paired-results.json')
paired=json.loads((public/'paired-results.json').read_text())
# case: seeded phase, iteration, prior page, log field, logged path, page expected
expected={'isa-render-absent':(None,None,False,None,None,False),
 'isa-render-first-authoring':('execute',1,False,'skipped','paired-work/ISA.md:pre-completion',False),
 'isa-render-missing':(None,None,False,'skipped','absent-work/ISA.md:missing',False),
 'isa-render-complete':('complete',1,False,'rendered','paired-work/ISA.md',True),
 'isa-render-resumed':('execute',2,False,'rendered','paired-work/ISA.md',True),
 'isa-render-existing-page':('execute',1,True,'rendered','paired-work/ISA.md',True)}
assert [case['id'] for case in paired['cases']]==list(expected)
document='LIFEOS/MEMORY/WORK/paired-work/ISA.md'
page_name='LIFEOS/MEMORY/WORK/paired-work/ISA.html'
log_name='LIFEOS/MEMORY/OBSERVABILITY/isa-render.jsonl'
decode=lambda files,name: base64.b64decode(files[name]['content_base64']).decode()
proof=[]
for case in paired['cases']:
 assert not case['errors'],case
 case_id=case['id']
 phase,iteration,prior,field,logged,rendered=expected[case_id]
 for side in ('native','hermes'):
  home=Path(config[side]['home_root'])/'results'/case_id
  destination=public/side/case_id;destination.mkdir(parents=True,exist_ok=True)
  result=json.loads((home/'result.json').read_text())
  for artifact,value in result['raw_artifacts'].items():
   assert sha(home/artifact)==value,(side,case_id,artifact)
   shutil.copy2(home/artifact,destination/artifact)
  shutil.copy2(home/'result.json',destination/'result.json')
  session=result['session_id']
  events=[json.loads(line) for line in (home/'fixture-events.jsonl').read_text().splitlines()]
  assert [row['hook_event_name'] for row in events]==['SessionStart','UserPromptSubmit','SessionEnd']
  assert {row['session_id'] for row in events}=={session}
  hooks=[json.loads(line) for line in (home/'hooks.jsonl').read_text().splitlines()]
  assert len(hooks)==1 and hooks[0]['id']=='Stop.1.4' and hooks[0]['exit_code']==0
  assert json.loads(hooks[0]['stdout'])=={'continue':True}
  payload=json.loads(base64.b64decode(hooks[0]['stdin_base64']))
  assert payload['hook_event_name']=='Stop' and payload['session_id']==session
  before=json.loads((home/'fixture-files-before.json').read_text())
  after=json.loads((home/'fixture-files-after.json').read_text())
  state_name='LIFEOS/MEMORY/STATE/isa-render-debounce/'+session+'.json'
  assert (state_name in before)==(case_id!='isa-render-absent') and state_name not in after
  work=str(home/'.claude/LIFEOS/MEMORY/WORK')+'/'
  if state_name in before:
   edited=json.loads(decode(before,state_name))['edited_isas']
   assert [value.replace(work,'',1) for value in edited]==[logged.split(':')[0]]
  assert (document in before)==(phase is not None)
  if phase:
   text=decode(before,document)
   assert f'\nphase: {phase}\n' in text and f'\niteration: {iteration}\n' in text
   assert after[document]==before[document]
  assert (page_name in before)==prior
  if prior:assert 'PAIR_PRIOR_PAGE' in decode(before,page_name)
  assert (page_name in after)==rendered
  page_sha=''
  if rendered:
   page=decode(after,page_name)
   assert 'PAIR_ISA_TITLE' in page and '<html' in page and 'PAIR_PRIOR_PAGE' not in page
   page_sha=hashlib.sha256(page.encode()).hexdigest()
  rows=[json.loads(line) for line in decode(after,log_name).splitlines()] if log_name in after else []
  assert log_name not in before and len(rows)==(1 if field else 0)
  if field:
   row=rows[0]
   assert row['session_id']==session
   other='skipped' if field=='rendered' else 'rendered'
   assert [value.replace(work,'',1) for value in row[field]]==[logged] and row[other]==[]
  cli=[]
  for text in (home/'cli.log').read_text().splitlines():
   try:row=json.loads(text)
   except ValueError:continue
   if isinstance(row,dict) and row.get('type')=='result':cli.append(row)
  assert len(cli)==1
  response=cli[0].get('result' if side=='native' else 'text','')
  assert 'READY' in response
  requests=json.loads((home/'requests-private.json').read_text())
  assert (home/'requests-private.json').stat().st_mode & 0o777==0o600
  generation=[row for row in requests if row['path'].startswith('/v1/')]
  assert len(generation)==1 and generation[0]['upstream_status']==200
  row=generation[0]
  for key in ('body','response_body'):
   assert hashlib.sha256(base64.b64decode(row[key+'_base64'])).hexdigest()==row[key+'_sha256']
  for definition in result['hook_definitions']:
   for path,value in definition['source_files'].items():assert sha(Path(path))==value
  proof.append({'case':case_id,'side':side,'session_id':session,'seeded_phase':phase,
   'seeded_iteration':iteration,'prior_page':prior,'state_cleared':True,
   'log_field':field,'logged_path':logged,'page_rendered':rendered,'page_sha256':page_sha,
   'document_preserved':True,'user_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
   'request_sha256':row['body_sha256'],'response_sha256':row['response_body_sha256'],
   'actual_model':row['actual_model'],'upstream_status':row['upstream_status']})
write(public/'render-proof.json',proof)
with tarfile.open(root/'public.tar.gz','w:gz') as archive:
 archive.add(public,arcname='paired-isa-render')
print(json.dumps({'verified_clients':len(proof),'verified_source_files':len(manifest['source_sha256']),
 'native_programs':len(runtime['native_program_sha256']),'archive':str(root/'public.tar.gz')}))
