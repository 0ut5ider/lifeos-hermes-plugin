# ABOUTME: Restores a killed native mount through the visible authenticated plugin control.
# ABOUTME: Records the browser outcome without credentials or session cookies.
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
cache=Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002')
out=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-02-mount-acceptance')
login=json.loads((cache/'browser-login.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1500,'height':1100})
 page.goto('http://192.168.8.212:8921/login')
 page.locator('input[name="username"]').fill(login['username'])
 page.locator('input[name="password"]').fill(login['password'])
 page.get_by_role('button',name='Sign in',exact=True).click()
 page.wait_for_url('http://192.168.8.212:8921/')
 page.get_by_role('link',name='LifeOS Bridge',exact=False).click()
 button=page.get_by_role('button',name='Restore interrupted mount',exact=True)
 button.wait_for(timeout=20000)
 page.screenshot(path=str(out/'acceptance-recovery-before.png'),full_page=True)
 with page.expect_response(lambda r:'/installation/mount/recover' in r.url and r.request.method=='POST',timeout=120000) as pending:
  button.click()
 response=pending.value
 result=dict(status=response.status,body=response.json())
 (out/'browser-recovery.json').write_text(json.dumps(result,indent=2)+'\n')
 assert response.status==200 and result['body']['state']=='rolled_back',result
 button.wait_for(state='hidden',timeout=20000)
 page.screenshot(path=str(out/'acceptance-recovery-after.png'),full_page=True)
 print(json.dumps({'browser_recovery':True,'state':'rolled_back'}))
 browser.close()
