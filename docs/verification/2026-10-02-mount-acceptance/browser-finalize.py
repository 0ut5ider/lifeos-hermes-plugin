# ABOUTME: Signs in to the isolated LAN dashboard through its actual browser login form.
# ABOUTME: Saves visible navigation and a screenshot without recording credentials or cookies.
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
home=Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002')
output=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-02-mount-acceptance')
credentials=json.loads((home/'browser-login.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 context=browser.new_context(viewport={'width':1440,'height':1100})
 page=context.new_page()
 page.goto('http://192.168.8.212:8921/login')
 page.locator('input[name="username"]').fill(credentials['username'])
 page.locator('input[name="password"]').fill(credentials['password'])
 page.get_by_role('button',name='Sign in',exact=True).click()
 page.wait_for_url('http://192.168.8.212:8921/',timeout=30000)
 page.get_by_role('link',name='LifeOS Bridge',exact=False).click()
 with page.expect_response(lambda r:'/installation/finalize' in r.url and r.request.method=='POST',timeout=120000) as pending:
  page.get_by_role('button',name='Finish LifeOS setup',exact=True).click()
 response=pending.value
 result={'status':response.status,'body':response.json()}
 (output/'browser-finalize.json').write_text(json.dumps(result,indent=2)+'\n')
 page.wait_for_timeout(1500)
 page.screenshot(path=str(output/'acceptance-finalized.png'),full_page=True)
 assert result['status']==200,result
 assert result['body']['mounted'] and result['body']['baseline_created'],result
 print(json.dumps({'browser_finalize':True,'state':result['body']['state'],'baseline_created':True}))
 browser.close()
