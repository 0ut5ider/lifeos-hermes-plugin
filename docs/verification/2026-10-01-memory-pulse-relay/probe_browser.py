# ABOUTME: Checks a browser session across actual native and dashboard localhost ports.
# ABOUTME: Uses the dashboard login form and native request cookies without token injection.
import json
import sys
from playwright.sync_api import sync_playwright

native,dashboard=sys.argv[1:]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context()
    page=context.new_page()
    response=page.goto(native+'/api/memory')
    assert response.status==401
    page.goto(dashboard+'/login')
    page.locator('input[name="username"]').fill('synthetic-owner')
    page.locator('input[name="password"]').fill('synthetic-password')
    page.get_by_role('button',name='Sign in',exact=True).click()
    page.wait_for_url(dashboard+'/')
    response=page.goto(native+'/api/memory')
    assert response.status==200, page.content()
    assert 'Synthetic authenticated PULSE fact' in page.content()
    checks=page.evaluate('''async () => {const results=[]; for(const path of ['/api/memory','/api/memory/state','/api/memory/health','/api/memory/runs']) {const response=await fetch(path,{cache:'no-store'}); results.push({path,status:response.status,cache:response.headers.get('cache-control')});} return results;}''')
    assert all(x['status']==200 and x['cache']=='no-store' for x in checks)
    other=context.new_page()
    other.goto(dashboard+'/')
    blocked=other.evaluate('''async (url) => {try {await fetch(url,{credentials:'include'}); return false;}catch {return true;}}''',native+'/api/memory')
    assert blocked
    other.evaluate('''async () => {await fetch('/auth/logout',{method:'POST'});}''')
    response=page.reload()
    assert response.status==401
    assert 'Synthetic authenticated PULSE fact' not in page.content()
    print(json.dumps({'browser':'Chromium','native_views':checks,'cross_origin_blocked':blocked,'after_logout':response.status}))
    browser.close()
