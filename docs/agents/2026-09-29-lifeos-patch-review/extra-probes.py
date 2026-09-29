# ABOUTME: Checks audit byte counts and native remote ISA state in isolated homes.
# ABOUTME: Records successful guard behavior and explicit missing-digest behavior.
from pathlib import Path
import os,json,hashlib,tempfile,subprocess
SRC=Path('/tmp/lifeos-astra-review-20260929/source/LifeOS/install')
results={}
with tempfile.TemporaryDirectory(prefix='lifeos-review-audit-') as tmp:
 root=Path(tmp);text='é🚀';env={**os.environ,'HOME':str(root),'LIFEOS_DIR':str(root/'LIFEOS')}
 payload={'hook_event_name':'PostToolUse','session_id':'audit-review','tool_name':'Bash','tool_input':{'command':'printf unicode'},'tool_response':{'output':text,'exit_code':0}}
 run=subprocess.run(['bun',str(SRC/'hooks/EventLogger.hook.ts')],input=json.dumps(payload),text=True,capture_output=True,env=env,check=True)
 row=json.loads((root/'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl').read_text().splitlines()[-1])
 results['unicode_audit']={'utf8_bytes':len(text.encode()),'ground_truth':row['ground_truth']}
with tempfile.TemporaryDirectory(prefix='lifeos-review-isa-') as tmp:
 root=Path(tmp);env={**os.environ,'HOME':str(root)};guard=SRC/'hooks/ISAStaleWriteGuard.hook.ts';driver=root/'driver.ts'
 driver.write_text('import {check} from '+json.dumps(str(guard))+'; console.log(JSON.stringify(check(JSON.parse(await Bun.stdin.text()))));')
 path='/remote/review/ISA.md'
 def payload(tool,value,status='file',identity='ssh-test'):
  return {'session_id':'isa-review','tool_name':tool,'tool_input':{'file_path':path,'lifeos_remote_file':{'identity':identity,'status':status,'sha256':hashlib.sha256(value.encode()).hexdigest()}}}
 def run(file,data):
  p=subprocess.run(['bun',str(file)],input=json.dumps(data),env=env,text=True,capture_output=True,check=True)
  return json.loads(p.stdout)
 results['isa_record']=run(guard,payload('Read','v1'))
 results['isa_changed']=run(driver,payload('Write','v2'))
 results['isa_unchanged']=run(driver,payload('Write','v1'))
 results['isa_unknown_digest']=run(driver,payload('Write','v2',status='error'))
 results['isa_other_backend']=run(driver,payload('Write','v2',identity='ssh-other'))
 run(guard,payload('Read','v2'))
 results['isa_refreshed']=run(driver,payload('Write','v2'))
print(json.dumps(results,indent=2))
