# ABOUTME: Records actual source-health HTTP responses and native comparison output.
# ABOUTME: Keeps synthetic sources and admitted metadata without login credentials.
import json, os, sys, subprocess, unittest
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
from test_memory_freshness_health import MemoryFreshnessHealthTests
from test_memory_freshness_health_current import MemoryFreshnessHealthCurrentTests
p=Path(__file__).resolve().parent/'native-outcomes'
p.mkdir(exist_ok=True)
original_request=httpx.Client.request
original_run=subprocess.run
requests=[]
events=[]
def request(client,method,url,*args,**kwargs):
 response=original_request(client,method,url,*args,**kwargs)
 if '/api/telos/' in str(url) or str(url).endswith('/api/freshness'):
  requests.append({'method':method,'url':str(url),'status':response.status_code,'body':response.text,
   'cache-control':response.headers.get('cache-control'),'content-type':response.headers.get('content-type')})
 return response
def run(*args,**kwargs):
 result=original_run(*args,**kwargs)
 command=args[0] if args else kwargs.get('args',[])
 if command and Path(command[0]).name=='bun':
  events.append({'command':command,'status':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 return result
httpx.Client.request=request
subprocess.run=run
count=0
try:
 for cls in (MemoryFreshnessHealthTests,MemoryFreshnessHealthCurrentTests):
  for name in unittest.defaultTestLoader.getTestCaseNames(cls):
   test=cls(name)
   test.setUp()
   requests=[]
   events=[]
   try:
    before={str(path.relative_to(test.root)):path.read_text() for path in (test.root/'LIFEOS/USER/TELOS').rglob('*.md')}
    getattr(test,name)()
    after={str(path.relative_to(test.root)):path.read_text() for path in (test.root/'LIFEOS/USER/TELOS').rglob('*.md')}
    record={'case':name,'before':before,'after':after,'requests':requests,'events':events,
      'native_source':os.environ['LIFEOS_MEMORY_SOURCE']}
    (p/(cls.__name__+'-'+name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    count+=1
   finally:
    test.doCleanups()
finally:
 httpx.Client.request=original_request
 subprocess.run=original_run
print(f'Recorded {count} passing source-health controls')
