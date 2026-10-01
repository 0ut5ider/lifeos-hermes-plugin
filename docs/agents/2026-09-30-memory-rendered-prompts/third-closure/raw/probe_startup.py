from pathlib import Path
import sys,json
from datetime import datetime,timezone
from dataclasses import replace
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_sources import MemorySourceTests
from lifeos_hook_bridge.memory_runtime import _generated_text,MemoryAdmissionError
for case in ('allowed','missing-context','unknown-author','restricted','broken-connector'):
 f=MemorySourceTests();f.setUp()
 try:
  now=datetime.now(timezone.utc);markers=['Synthetic relationship closure marker','Synthetic wisdom closure marker','Synthetic advisory closure marker','Synthetic progress closure marker']
  f.source('RELATIONSHIP/'+now.strftime('%Y-%m/%Y-%m-%d.md'),'- '+markers[0]+'\n')
  f.source('WISDOM/FRAMES/synthetic.md','### '+markers[1]+' [CRYSTAL: 95%]\n')
  f.source('STATE/events.jsonl',json.dumps({'type':'doc.integrity.memory_dir','source':'synthetic','timestamp':now.isoformat(),'findings':[{'key':'fixture','detail':markers[2]}]})+'\n')
  f.source('STATE/progress/synthetic-progress.json',json.dumps({'project':markers[3],'status':'active','updated':now.isoformat(),'objectives':[],'next_steps':[],'handoff_notes':''}))
  if case=='unknown-author':f.fixture.context=replace(f.fixture.context,author='unknown')
  if case=='restricted':
   cfg=f.fixture.configuration.load();cfg['destinations']['chat-a:200'].update(read=['project'],projects=['lab']);f.fixture.configuration.save(cfg)
  if case=='broken-connector':
   p=f.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json';p.unlink();p.symlink_to(p.parent/'missing.json')
  output=f.startup(channel='chat-a',context=case!='missing-context')
  present=[m for m in markers if m in output];print(json.dumps({'case':case,'present':present,'output':output}),flush=True)
  assert len(present)==(4 if case=='allowed' else 0)
 finally:f.doCleanups()
for case in ('deep','cycle','nested-lazy'):
 if case=='deep':
  value='Synthetic leaf'
  for _ in range(34):value=[value]
 elif case=='cycle':value=[];value.append(value)
 else:value={'output':(v for v in ['Synthetic leaf'])}
 try:_generated_text(value)
 except MemoryAdmissionError as error:print(json.dumps({'case':case,'rejected':True,'reason':str(error)}),flush=True)
 else:raise AssertionError(case+' was not rejected')
 if case=='nested-lazy':assert list(value['output'])==['Synthetic leaf']
