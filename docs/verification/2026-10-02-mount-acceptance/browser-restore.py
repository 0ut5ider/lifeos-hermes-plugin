# ABOUTME: Exercises the installed restore button with an actual browser owner session.
# ABOUTME: Verifies that later memory changes refuse restoration and preserve update status.
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

cache = Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002')
out = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-02-mount-acceptance')
login = json.loads((cache / 'browser-login.json').read_text())
base = 'http://192.168.8.212:8921'
endpoint = base + '/api/plugins/lifeos-hook-bridge/installation/update'
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1500, 'height': 1100})
    page.goto(base + '/login')
    page.locator('input[name="username"]').fill(login['username'])
    page.locator('input[name="password"]').fill(login['password'])
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url(base + '/')
    page.get_by_role('link', name='LifeOS Bridge', exact=False).click()
    before = page.request.get(endpoint).json()
    with page.expect_response(endpoint + '/restore') as response:
        page.get_by_role('button', name='Restore previous LifeOS version', exact=True).click()
    result = response.value
    page.get_by_text('Could not restore LifeOS:', exact=False).wait_for()
    after = page.request.get(endpoint).json()
    page.screenshot(path=str(out / 'acceptance-restore-refusal.png'), full_page=True)
    record = {'status': result.status, 'response': result.json(),
              'before': before, 'after': after, 'update_status_unchanged': before == after}
    (out / 'browser-restore.json').write_text(json.dumps(record, indent=2) + '\n')
    assert result.status == 409, record
    assert 'User data changed' in result.json()['detail'], record
    assert before == after, record
    print(json.dumps({'restore_refusal_verified': True, 'status': result.status, 'update_state': after['state']}))
    browser.close()
