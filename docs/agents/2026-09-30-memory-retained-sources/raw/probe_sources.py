from pathlib import Path
from datetime import datetime,timezone
import sys,json
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_sources import MemorySourceTests
from test_memory_native import OWNER
for case in ('work-filename','advisory-redirect','broken-connector'):
 f=MemorySourceTests();f.setUp()
 try:
  if case=='work-filename':
   marker='Synthetic forgotten work title marker'
   saved=f.memory.remember(OWNER,category='principal',content='RULE: '+marker,title='',project='',request_id='marker')
   f.memory.forget(OWNER,saved['reference'],'forget-marker')
   path=f.source('WORK/'+datetime.now().strftime('%Y%m%d-%H%M%S_')+marker.replace(' ','-')+'/ISA.md','phase: build\n')
   direct=f.service.native(f.fixture.context,'read_source',{'path':str(path)})
   out=f.startup();print(json.dumps({'case':case,'direct':direct,'marker_in_startup':marker in out,'startup':out}),flush=True)
  elif case=='advisory-redirect':
   marker='SYNTHETIC_CONFIG_ONLY_ADVISORY_MARKER'
   secret=f.fixture.root/'LIFEOS/USER/CONFIG/synthetic-secret.jsonl'
   secret.write_text(json.dumps({'type':'doc.integrity.memory_dir','source':'synthetic','timestamp':datetime.now(timezone.utc).isoformat(),'findings':[{'key':'synthetic','detail':marker}]})+'\n')
   path=f.source('STATE/events.jsonl','');path.unlink();path.symlink_to(secret)
   direct=f.service.native(f.fixture.context,'read_source',{'path':str(path)})
   out=f.reader('loadAdvisoryDigest',library='advisory-readback.ts');print(json.dumps({'case':case,'direct':direct,'digest':out}),flush=True)
  else:
   f.source('WISDOM/FRAMES/synthetic.md','### Synthetic broken connector marker [CRYSTAL: 95%]\n')
   cfg=f.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json';cfg.unlink();cfg.symlink_to(cfg.parent/'missing.json')
   out=f.reader('loadWisdomFrames');print(json.dumps({'case':case,'output':out}),flush=True)
 finally:f.doCleanups()
