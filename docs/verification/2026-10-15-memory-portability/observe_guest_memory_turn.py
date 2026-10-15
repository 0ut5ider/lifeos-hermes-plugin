# ABOUTME: Executes a fresh installed Hermes model turn against synthetic portability memory.
# ABOUTME: Keeps raw output private and exports only bounded acceptance metadata.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=('native-read','builtin-read'))
parser.add_argument('--label',required=True)
args=parser.parse_args()
home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if Path.home()!=home or os.getuid()!=1000:
    raise RuntimeError('Use the disposable guest owner account')
if not args.label or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for character in args.label):
    raise ValueError('Use a bounded acceptance label')
output=home/'install-input/model-turns'/args.label
output.mkdir(parents=True,mode=0o700)
query=('Use lifeos_memory_search exactly once with query "synthetic portability project marker". '
       'Return the matched fact and its reference. Do not use shell, files, or earlier chat history.'
       if args.mode=='native-read' else
       'What is the synthetic portability project marker in your lasting memory? '
       'Answer only the marker. Do not use tools, shell, files, or earlier chat history.')
query_path=output/'query.txt';query_path.write_text(query+'\n')
command=[str(home/'.local/bin/hermes'),'chat','--query-file',str(query_path),
    '--oneshot','--format','stream-json','--max-turns','4','--run-budget','120']
started=time.monotonic();receipt={'mode':args.mode,'status':'FAIL','model_turn_executed':False,
    'fresh_session':True,'configured_route_used':True,'daily_changed':False}
try:
    with (output/'stdout.jsonl').open('wb') as stdout,(output/'stderr.txt').open('wb') as stderr:
        result=subprocess.run(command,cwd=profile,stdout=stdout,stderr=stderr,timeout=180)
    events=[]
    for line in (output/'stdout.jsonl').read_text().splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if isinstance(event,dict):events.append(event)
    final=[event for event in events if event.get('type')=='result']
    final=final[-1] if final else {}
    tool_events=[event for event in events if event.get('type')=='tool_use']
    names=[event.get('name') for event in tool_events]
    expected='D244-MEMORY-1015'
    marker_matched=expected in final.get('text','')
    model_turn=final.get('tokens',{}).get('output',0)>0
    tool_match=(names==['lifeos_memory_search'] if args.mode=='native-read' else not names)
    receipt.update(exit_code=result.returncode,model_turn_executed=model_turn,
        marker_matched=marker_matched,tool_names=names,expected_tool_selection=tool_match,
        final_sha256=hashlib.sha256(final.get('text','').encode()).hexdigest(),
        session_id=final.get('session_id'),model=next((event.get('model') for event in events
            if event.get('type')=='system' and event.get('subtype')=='init'),None))
    if result.returncode==0 and final.get('exit_code')==0 and marker_matched and model_turn and tool_match:
        receipt['status']='PASS'
except Exception as error:
    receipt['error_type']=type(error).__name__
finally:
    receipt['elapsed_seconds']=time.monotonic()-started
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'observation.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
