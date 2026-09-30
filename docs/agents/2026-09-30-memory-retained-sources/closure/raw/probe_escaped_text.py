from pathlib import Path
import sys,json
from datetime import datetime,timezone
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_sources import MemorySourceTests
from test_memory_native import OWNER
for case in ('advisory-newline','progress-newline'):
 f=MemorySourceTests();f.setUp()
 try:
  marker='Synthetic forgotten escaped marker'
  saved=f.memory.remember(OWNER,category='principal',content='RULE: '+marker,title='',project='',request_id='escaped')
  f.memory.forget(OWNER,saved['reference'],'forget-escaped')
  encoded=marker.replace('forgotten ','forgotten\n')
  if case=='advisory-newline':out=f.advisory(encoded)
  else:
   f.source('STATE/progress/synthetic-progress.json',json.dumps({'project':encoded,'status':'active','updated':datetime.now(timezone.utc).isoformat(),'objectives':[],'next_steps':[],'handoff_notes':''}))
   out=f.startup()
  print(json.dumps({'case':case,'normalized_marker_emitted':marker in ' '.join((out or '').split()),'output':out}),flush=True)
 finally:f.doCleanups()
