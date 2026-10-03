from pathlib import Path
import sys,json,os,time
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
from test_memory_adoption import MemoryAdoptionTests
for case in ('learning-title-equals-body','learning-trailing-space','mtime-preview','hot-wrapped-forgotten'):
 f=MemoryAdoptionTests();f.setUp();m=f.memory
 try:
  if case=='hot-wrapped-forgotten':
   claim='Synthetic retired routing port 8123'
   r=m.remember(f.scope,category='principal',content='RULE: '+claim,title='',project='',request_id='old')
   m.forget(f.scope,r['reference'],'forget')
   n=m._native('add',item={'type':'memory','actor':'principal','content':'RULE: Historical note says '+claim+' in retained history.'})
  else:
   n=m.root/'LIFEOS/MEMORY/LEARNING/SYSTEM/2026-09/probe.md';n.parent.mkdir(parents=True)
   if case=='learning-title-equals-body':n.write_text('---\ntype: learning\ntitle: Synthetic repeated title marker\n---\nSynthetic repeated title marker\n')
   elif case=='learning-trailing-space':n.write_text('Synthetic trailing whitespace marker   \n')
   else:
    n.write_text('Synthetic independent learning marker\n');os.utime(n,(1,1))
    r=m.remember(f.scope,category='principal',content='RULE: Synthetic retired unrelated preference',title='',project='',request_id='old')
    m.forget(f.scope,r['reference'],'forget')
  p=m.preview_adoption(f.scope)
  if case=='mtime-preview':os.utime(n,(time.time()+100,time.time()+100))
  a=m.adopt(f.scope,p['signature'],{},'adopt-probe')
  try:found=m.recall(f.scope,'Synthetic marker routing');error=None
  except Exception as e:found=None;error=repr(e)
  print(json.dumps({'case':case,'preview_count':len(p['records']),'excluded':p['excluded'],'receipt':a,'recall':found,'error':error}),flush=True)
 finally:f.doCleanups()
