# ABOUTME: Changes real publication destinations at deterministic after-write boundaries.
# ABOUTME: Records native response, operation receipt, journal and artifact-group consistency.
import json,sqlite3
from contextlib import closing
from pathlib import Path
from lifeos_hook_bridge import memory_transaction, memory_conduit_insight
from lifeos_hook_bridge.memory_service import MemoryService
import test_memory_local_refresh_publication as local
import test_memory_conduit_insight as conduit

def receipts(memory):
 with closing(sqlite3.connect(memory.database)) as c: return [json.loads(row[0]) for row in c.execute('SELECT receipt FROM operations')]

def execute(kind):
 if kind=='local':
  f=local.MemoryLocalRefreshPublicationTests();f.setUp(); prepared=f.prepare();requested=f.digest(); later=json.loads(json.dumps(requested));later['news']['items'][0]['title']='Synthetic later owner destination edit.';dest=f.dated(prepared);module=memory_transaction;memory=f.owner.fixture.memory
 else:
  f=conduit.MemoryConduitInsightTests();f.setUp();prepared=f.prepare(initialize=True);requested={'date':f.date,'generatedAt':'2026-10-09T12:00:00Z','conduitVersion':'1.0.0','level':'low','model':'(none)','since':None,'eventsConsidered':0,'skipped':True,'narrative':'No activity captured yet today.','contentTypes':[]};later=dict(requested,generatedAt='2026-10-09T12:01:00Z');dest=f.insight;module=memory_conduit_insight;memory=f.fixture.fixture.memory
 original=module.publish;events=[]
 def observed(path,data):
  original(path,data)
  if path==dest: path.write_text(json.dumps(later));events.append(str(path))
 module.publish=observed
 try:
  response=f.publish(prepared,requested) if kind=='local' else MemoryService(f.fixture.configuration).native(f.fixture.context,'conduit_publish',{'date':f.date,'initialize':True,'signature':prepared['signature'],'value':requested,'reuse':False})
 finally:module.publish=original
 result={'kind':kind,'response':response,'receipts':receipts(memory),'journal':memory.transaction.journal.exists(),'destination_matches_requested':json.loads(dest.read_text())==requested,'destination_matches_later':json.loads(dest.read_text())==later,'events':events}
 if kind=='local':result['latest_match_requested']=[json.loads((f.root/name).read_text())==requested for name in [local.PRIMARY,local.FALLBACK]]
 else:result['config_exists']=f.config.exists()
 try:
  with memory._transaction():pass
  result['fresh_transaction']='success';result['journal_after_recovery']=memory.transaction.journal.exists();result['receipts_after_recovery']=receipts(memory);result['destination_still_matches_later']=dest.exists() and json.loads(dest.read_text())==later
 except Exception as e:result['fresh_transaction']=type(e).__name__+': '+str(e)
 f.doCleanups();return result
print(json.dumps([execute(kind) for kind in ('local','conduit')],indent=2))
