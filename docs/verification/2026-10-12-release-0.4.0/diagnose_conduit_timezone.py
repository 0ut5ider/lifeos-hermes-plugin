# ABOUTME: Measures timezone differences between direct and governed Conduit fixture calls.
# ABOUTME: Records only synthetic event filenames, timestamps, and assertion results from actual native processes.
import json,os,sys
from pathlib import Path
package=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/packages/0.4.0-a87e7ae9')
sys.path[:0]=[str(package),str(package/'tests'),str(package/'hermes')]
from test_memory_conduit_capture import MemoryConduitCaptureTests
rows=[]
for zone in ('America/Toronto','UTC'):
 os.environ['TZ']=zone
 test=MemoryConduitCaptureTests('test_processed_private_work_never_enters_native_capture');test.setUp()
 try:
  status='PASS';failure=None
  try:test.test_processed_private_work_never_enters_native_capture()
  except AssertionError as error:status='FAIL';failure=str(error)
  events=[{'file':p.name,'ts':e['ts'],'last_slug':e['detail'].get('lastSlug')} for p in sorted((test.data/'events').glob('*.jsonl')) for e in map(json.loads,p.read_text().splitlines())]
  rows.append({'governed_timezone':zone,'direct_fixture_timezone':'UTC','status':status,'failure':failure,'events_in_fixture_order':events})
 finally:test.doCleanups()
print(json.dumps({'cases':rows,'real_native_processes':True,'product_sources_changed':False},indent=2))
