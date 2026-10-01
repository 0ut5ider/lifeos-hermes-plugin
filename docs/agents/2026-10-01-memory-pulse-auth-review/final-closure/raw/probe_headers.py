import asyncio,json
import httpx
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from test_memory_pulse_auth import MemoryPulseAuthTests
c=MemoryPulseAuthTests();c.setUp()
try:
 install=next(m.cls.__call__.__globals__['install_memory_cache_headers'] for m in c.app.user_middleware if m.cls.__name__=='MemoryResponseHeaders')
 app=FastAPI()
 @app.get('/{path:path}')
 async def echo(path:str,request:Request):
  await asyncio.sleep(0)
  return JSONResponse({'path':path,'tag':request.headers['x-synthetic-tag']},headers={'Cache-Control':'public, max-age=60','ETag':'synthetic-etag','Last-Modified':'Wed, 21 Oct 2015 07:28:00 GMT','X-Preserved':'yes'})
 install(app);install(app)
 assert len(app.user_middleware)==1
 async def run():
  cases=[]
  for root in ('','/deployment'):
   async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,root_path=root),base_url='http://synthetic.local') as client:
    async def one(i):
     protected=i%2==0
     path=root+(c.endpoint+'snapshot' if protected else '/api/plugins/lifeos-hook-bridge/memory/pulsex/snapshot')
     r=await client.get(path,headers={'X-Synthetic-Tag':str(i)})
     assert r.json()['tag']==str(i) and r.headers['x-preserved']=='yes'
     assert r.headers['cache-control']==('no-store' if protected else 'public, max-age=60')
     assert ('etag' not in r.headers)==protected and ('last-modified' not in r.headers)==protected
     return {'root_path':root,'protected':protected,'status':r.status_code,'cache_control':r.headers['cache-control']}
    cases.extend(await asyncio.gather(*(one(i) for i in range(20))))
  return cases
 print(json.dumps({'middleware_count':len(app.user_middleware),'concurrent_cases':asyncio.run(run())},indent=2))
finally:c.doCleanups()
