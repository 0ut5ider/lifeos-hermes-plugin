# ABOUTME: Exercises native handler admission with a real LAN browser password session.
# ABOUTME: Captures statuses and visible routes without credentials or session tokens.
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
cache=Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002')
out=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-02-mount-acceptance')
login=json.loads((cache/'browser-login.json').read_text())
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 ctx=browser.new_context(viewport={'width':1400,'height':1000})
 page=ctx.new_page()
 def request(path,method='GET',body=None):
  return page.evaluate('''async ({path,method,body})=>{const r=await fetch(path,{method,headers:body===null?{}:{'Content-Type':'application/json'},body:body===null?undefined:JSON.stringify(body)});return {status:r.status,cache:r.headers.get('cache-control'),body:await r.json()}}''',dict(path=path,method=method,body=body))
 page.goto('http://192.168.8.212:8922/api/memory')
 results.append(dict(case='anonymous',**request('/api/memory')))
 page.goto('http://192.168.8.212:8921/login')
 page.locator('input[name="username"]').fill(login['username'])
 page.locator('input[name="password"]').fill(login['password'])
 page.get_by_role('button',name='Sign in',exact=True).click()
 page.wait_for_url('http://192.168.8.212:8921/')
 page.goto('http://192.168.8.212:8922/api/memory')
 for path in ['/api/memory','/api/memory/state','/api/memory/health','/api/memory/runs']:
  results.append(dict(case=path,**request(path)))
 results.append(dict(case='remount',**request('/api/hermes/remount','POST')))
 results.append(dict(case='body-refusal',**request('/api/hermes/remount','POST',{'home':'other'})))
 results.append(dict(case='query-refusal',**request('/api/hermes/remount?home=other','POST')))
 results.append(dict(case='unexposed-route',**request('/api/hermes/soul')))
 page.screenshot(path=str(out/'acceptance-native-memory.png'),full_page=True)
 # A foreign Origin must fail even with a valid session.
 r=ctx.request.post('http://192.168.8.212:8922/api/hermes/remount',headers={'Origin':'https://other.invalid'})
 results.append(dict(case='cross-origin',status=r.status,body=r.json()))
 # Clear actual browser credentials to test loss of authority.
 ctx.clear_cookies()
 page.goto('http://192.168.8.212:8922/api/memory')
 results.append(dict(case='session-cleared',**request('/api/memory')))
 (out/'browser-native.json').write_text(json.dumps(results,indent=2)+'\n')
 expected=[401,200,200,200,200,200,400,400,404,403,401]
 assert [x['status'] for x in results]==expected,[(x['case'],x['status']) for x in results]
 assert all(x.get('cache')=='no-store' for x in results[:9])
 print(json.dumps({'cases':len(results),'statuses':[x['status'] for x in results],'native_browser_acceptance':True}))
 browser.close()
