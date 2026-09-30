# ABOUTME: Checks real native diverted proposal identity collisions and retries.
# ABOUTME: Uses distinct synthetic claims with equal native slug prefixes in temporary fixtures.
from pathlib import Path
import sys,json,time
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
f=MemoryProposalTests();f.setUp()
try:
 prefix='SyntheticLab must use a dedicated deployment checklist with '
 results=[]
 for i in range(8):
  text=prefix+'distinct synthetic requirement number '+str(i)
  result=f.enqueue('collision-'+str(i),f.item(text))
  results.append({'edit':text,'result':result})
 paths={x['result']['receipt']['destination'] for x in results}
 print(json.dumps({'results':results,'distinct_destinations':len(paths),'published':{path:Path(path).read_text() for path in paths}},sort_keys=True),flush=True)
 retry=f.enqueue('collision-0',f.item(results[0]['edit']))
 print(json.dumps({'retry_first':retry,'retry_destination_contains_original':results[0]['edit'] in Path(retry['receipt']['destination']).read_text()},sort_keys=True),flush=True)
finally:f.doCleanups()
