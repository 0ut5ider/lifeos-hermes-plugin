# ABOUTME: Observes an actual Algorithm summary publication followed by a later destination edit.
# ABOUTME: Records persisted response, receipt, journal and recovery behavior on synthetic files.
import json,sqlite3
from contextlib import closing
import test_memory_algorithm_summary as fixtures
from lifeos_hook_bridge import memory_algorithm_summary as module
f=fixtures.MemoryAlgorithmSummaryTests();f.setUp()
try:
 p=f.prepare(); requested=f.value(p); later=json.loads(json.dumps(requested));later['files']['operational-rules']['markdown']='Synthetic later owner cache edit.'
 original=module.publish; events=[]
 def observed(path,data):
  original(path,data)
  if path==f.cache:
   path.write_text(json.dumps(later));events.append(str(path))
 module.publish=observed
 try: response=f.call('algorithm_summary_publish',signature=p['signature'],value=requested)
 finally: module.publish=original
 m=f.owner.fixture.memory
 with closing(sqlite3.connect(m.database)) as c: receipts=[json.loads(row[0]) for row in c.execute('SELECT receipt FROM operations')]
 print(json.dumps({'response':response,'journal':m.transaction.journal.exists(),'receipts':receipts,'cache_matches_requested':json.loads(f.cache.read_text())==requested,'cache_matches_later':json.loads(f.cache.read_text())==later,'events':events},indent=2))
finally:f.doCleanups()
