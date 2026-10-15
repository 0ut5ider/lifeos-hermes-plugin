# ABOUTME: Adds a synthetic later fact through the actual Hermes model and built-in memory tool.
# ABOUTME: Verifies successful tool publication and preserves prior current memory without exporting content.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
parser=argparse.ArgumentParser()
parser.add_argument('phase',choices=('after-return','after-removal'))
args=parser.parse_args()
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
assert os.getuid()==1000 and Path.home()==home
output=home/'install-input/model-turns'/('builtin-edit-'+args.phase)
output.mkdir(mode=0o700)
fact={'after-return':'Synthetic memory added after provider return is D244-LATER-RETURN-1015.',
    'after-removal':'Synthetic memory added after complete software removal is D244-LATER-REMOVAL-1015.'}[args.phase]
query=output/'query.txt'
query.write_text('Use the memory tool exactly once with action "add", target "memory", and content '+json.dumps(fact)+'. '
    'Preserve every existing entry. Report only the actual tool success status. Do not use shell or files.\n')
memory=profile/'memories/MEMORY.md';before=memory.read_bytes()
started=time.monotonic();receipt={'status':'FAIL','phase':args.phase,'daily_changed':False,
    'fresh_session':True,'raw_content_exported':False}
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
    after=memory.read_bytes()
    receipt.update(exit_code=result.returncode,session_id=final.get('session_id'),
        model_turn_executed=final.get('tokens',{}).get('output',0)>0,
        exact_tool_selection=[event.get('name') for event in calls]==['memory'],
        actual_tool_success=len(results)==1 and results[0].get('name')=='memory'
            and results[0].get('is_error') is False and actual.get('success') is True and not actual.get('staged'),
        later_fact_published=fact.encode() in after,prior_memory_preserved=before.strip() in after,
        before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest())
    if (result.returncode==0 and final.get('exit_code')==0 and all(receipt[key] for key in
            ('model_turn_executed','exact_tool_selection','actual_tool_success','later_fact_published','prior_memory_preserved'))):
        receipt['status']='PASS'
except Exception as error:
    receipt['error_type']=type(error).__name__
finally:
    receipt['elapsed_seconds']=time.monotonic()-started
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'observation.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
