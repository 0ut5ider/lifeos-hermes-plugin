# ABOUTME: Executes an actual model retrieval of an authorized imported fact by its native reference.
# ABOUTME: Compares the private tool output with the original source digest without exporting content.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
assert os.getuid()==1000 and Path.home()==home
reference={'id':'40500bb648b444198c863fc9a4207b7f','revision':1}
output=home/'install-input/model-turns/native-imported-fact'
output.mkdir(mode=0o700)
query=output/'query.txt'
query.write_text('Use lifeos_memory_get exactly once with reference '+json.dumps(reference)+'. '
    'Report only whether the tool status is ok and the reference matches. Do not quote the memory content. '
    'Do not use shell, files, or earlier chat history.\n')
started=time.monotonic();receipt={'status':'FAIL','fresh_session':True,'daily_changed':False,
    'reference':reference,'raw_content_exported':False}
try:
    with (output/'stdout.jsonl').open('wb') as stdout,(output/'stderr.txt').open('wb') as stderr:
        result=subprocess.run([str(home/'.local/bin/hermes'),'chat','--query-file',str(query),
            '--oneshot','--format','stream-json','--max-turns','4','--run-budget','120'],
            cwd=profile,stdout=stdout,stderr=stderr,timeout=180)
    events=[]
    for line in (output/'stdout.jsonl').read_text().splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if isinstance(event,dict):events.append(event)
    calls=[event for event in events if event.get('type')=='tool_use']
    results=[event for event in events if event.get('type')=='tool_result']
    final=next((event for event in reversed(events) if event.get('type')=='result'),{})
    actual=json.loads(results[0]['output']) if len(results)==1 else {}
    content=actual.get('content','');digest=hashlib.sha256(content.encode()).hexdigest()
    receipt.update(exit_code=result.returncode,session_id=final.get('session_id'),
        model_turn_executed=final.get('tokens',{}).get('output',0)>0,
        exact_tool_selection=[event.get('name') for event in calls]==['lifeos_memory_get'],
        actual_tool_ok=len(results)==1 and results[0].get('name')=='lifeos_memory_get'
            and results[0].get('is_error') is False and actual.get('status')=='ok',
        exact_reference=actual.get('reference')==reference,content_sha256=digest,
        original_source_digest_matches=False)
    expected=(home/'install-input/authorized-213-source-digest.txt').read_text().strip()
    receipt['original_source_digest_matches']=digest==expected
    if (result.returncode==0 and final.get('exit_code')==0 and all(receipt[key] for key in
            ('model_turn_executed','exact_tool_selection','actual_tool_ok','exact_reference','original_source_digest_matches'))):
        receipt['status']='PASS'
except Exception as error:
    receipt['error_type']=type(error).__name__
finally:
    receipt['elapsed_seconds']=time.monotonic()-started
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'observation.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
