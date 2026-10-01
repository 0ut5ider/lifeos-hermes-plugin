# ABOUTME: Checks exact diagnostic wire limits and native UTF-16 sample parity.
# ABOUTME: Exercises retained long-row text before display projection in synthetic fixtures.
import json
from datetime import datetime,timezone
from test_memory_diagnostics import MemoryDiagnosticTests
from lifeos_hook_bridge.memory_service import MemoryService
c=MemoryDiagnosticTests();c.setUp()
try:
 service=MemoryService(c.fixture.configuration)
 edits=['x'*79+'😀'+'Current emoji tail','x'*80+'😀'+'Current emoji tail','x'*78+'😀'+'Current emoji tail','x'*80,'x'*81]
 connector=c.root/'LIFEOS/USER/CONFIG/memory-access.json';cfg=connector.read_bytes()
 path=c.write('pending-proposals.jsonl',[c.proposal(edit,id='unicode-'+str(i)) for i,edit in enumerate(edits)])
 managed=c.call('MemoryInsights.ts').stdout
 connector.unlink();unmanaged=c.call('MemoryInsights.ts',context=False).stdout
 connector.write_bytes(cfg);connector.chmod(0o600)
 lines=lambda s:[line for line in s.splitlines() if line.strip().startswith('•')]
 # Native displays only the last three rows, check each boundary separately too.
 assert lines(managed)==lines(unmanaged)
 rows=[]
 for i,edit in enumerate(edits):
  c.write('pending-proposals.jsonl',[c.proposal(edit,id='unicode-'+str(i))])
  m=c.call('MemoryInsights.ts').stdout
  connector.unlink();u=c.call('MemoryInsights.ts',context=False).stdout
  connector.write_bytes(cfg);connector.chmod(0o600)
  assert lines(m)==lines(u),(m,u)
  rows.append({'edit':edit,'managed':lines(m),'unmanaged':lines(u)})
 print(json.dumps({'case':'utf16-parity','rows':rows}),flush=True)
 c.retire('Synthetic retired diagnostic final tail')
 c.now=datetime.now(timezone.utc).isoformat()
 row=c.proposal('Synthetic permitted-looking prefix. '+'abc '*10000+'Synthetic retired diagnostic final tail')
 path=c.write('pending-proposals.jsonl',[row,c.proposal('Synthetic current final-tail control',id='control')])
 path.write_text(path.read_text().replace('Synthetic retired diagnostic final tail',''.join('\\u%04x'%ord(x) for x in 'Synthetic retired diagnostic final tail')))
 out=c.call('MemoryInsights.ts').stdout
 assert 'Synthetic permitted-looking prefix' not in out and 'Synthetic retired diagnostic final tail' not in out
 assert 'Synthetic current final-tail control' in out and 'Proposals (2 total in window)' in out
 print(json.dumps({'case':'long-decoded-retired-tail','stdout':out}),flush=True)
 path.unlink()
 path=c.write('reviewer-runs.jsonl',[c.reviewer()])
 response=service.native(c.fixture.context,'read_diagnostic',{'path':str(path)})
 one=len((json.dumps(response)+'\n').encode())
 c.write('reviewer-runs.jsonl',[c.reviewer()]*2)
 response=service.native(c.fixture.context,'read_diagnostic',{'path':str(path)})
 two=len((json.dumps(response)+'\n').encode())
 cap=3*1024*1024
 count=1+(cap-one)//(two-one)
 measured=[]
 for n in (count,count+1):
  c.write('reviewer-runs.jsonl',[c.reviewer()]*n)
  response=service.native(c.fixture.context,'read_diagnostic',{'path':str(path)})
  if n==count:
   assert response['ok']
   wire=len((json.dumps(response)+'\n').encode());assert wire<=cap
  else:
   assert not response['ok'] and 'limit' in response['message'];wire=None
  measured.append({'rows':n,'ok':response['ok'],'wire_bytes':wire,'message':response.get('message')})
 print(json.dumps({'case':'exact-wire-boundary','cap':cap,'rows':measured}),flush=True)
finally:c.doCleanups()
