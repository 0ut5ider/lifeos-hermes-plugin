# ABOUTME: Restores the locally rehearsed update through the actual browser control.
# ABOUTME: Polls the real detached worker and requires a verified rolled-back result.
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

cache = Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002')
out = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-02-mount-acceptance')
login = json.loads((cache / 'browser-login.json').read_text())
base = 'http://192.168.8.212:8921'
endpoint = base + '/api/plugins/lifeos-hook-bridge/installation/update'
history = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1500, 'height': 1100})
    page.goto(base + '/login')
    page.locator('input[name="username"]').fill(login['username'])
    page.locator('input[name="password"]').fill(login['password'])
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url(base + '/')
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        status = page.request.get(endpoint).json()
        history.append(status)
        if status['state'] not in {'queued', 'preparing', 'applying'}:
            break
        page.wait_for_timeout(2000)
    (out / 'repeat-update-result.json').write_text(json.dumps(history, indent=2) + '\n')
    assert history[-1]['state'] == 'applied', history[-1]
    page.get_by_role('link', name='LifeOS Bridge', exact=False).click()
    with page.expect_response(endpoint + '/restore') as response:
        page.get_by_role('button', name='Restore previous LifeOS version', exact=True).click()
    result = response.value
    history.append({'restore_request_status': result.status, 'response': result.json()})
    deadline = time.monotonic() + 120
    while result.status == 200 and time.monotonic() < deadline:
        status = page.request.get(endpoint).json()
        history.append(status)
        if status['state'] not in {'restoring', 'recovering'}:
            break
        page.wait_for_timeout(2000)
    page.reload()
    page.wait_for_timeout(1000)
    page.screenshot(path=str(out / 'acceptance-restore-success.png'), full_page=True)
    (out / 'browser-restore-success.json').write_text(json.dumps(history, indent=2) + '\n')
    assert result.status == 200, history[-1]
    assert history[-1]['state'] == 'rolled_back', history[-1]
    print(json.dumps({'restore_verified': True, 'request': result.status, 'state': history[-1]['state']}))
    browser.close()
