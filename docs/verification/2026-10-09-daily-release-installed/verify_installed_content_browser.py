# ABOUTME: Exercises native Content run and confirmed disposal controls through real Chromium interactions.
# ABOUTME: Records actual HTTP responses and verifies the synthetic fixture effects on the installed server.
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import time
from playwright.sync_api import sync_playwright

evidence = Path(__file__).resolve().parent
stage = '/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7'
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
def fixture(action):
    result = subprocess.run(['ssh', 'root@192.168.8.252', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-I', '-B', stage + '/content_browser_fixture.py', action], capture_output=True, text=True, timeout=30)
    assert (result.returncode, result.stderr) == (0, ''), result.stdout + result.stderr
    return json.loads(result.stdout)
assert fixture('prepare')['prepared']
started = time.monotonic()
observations = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://localhost:18819/login?next=/')
    page.locator('input[name=username]').fill('acceptance-owner')
    page.locator('input[name=password]').fill('synthetic-application-acceptance-password')
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url('http://localhost:18819/')
    page.goto('http://localhost:18837/content', wait_until='domcontentloaded')
    title = 'Synthetic browser Content acceptance'
    page.get_by_text(title, exact=True).wait_for(state='visible')
    page.get_by_text(re.compile('^live$', re.I)).wait_for(state='visible')
    with page.expect_response(lambda response: response.request.method == 'POST'
            and response.url.endswith('/api/content/dailysynthetic4111/run')) as pending:
        page.get_by_role('button', name='\u25b6 RUN', exact=True).click()
    response = pending.value
    body = response.json()
    assert response.status == 200 and body['requested_run'] == 'regular', body
    observations.append({'action': 'run', 'status': response.status, 'body': body,
        'cache_control': response.headers.get('cache-control')})
    page.get_by_text('RUN QUEUED', exact=True).wait_for(state='visible')
    page.screenshot(path=str(evidence / 'installed-browser-content-queued.png'), full_page=True)
    def cancel(dialog): dialog.dismiss()
    page.once('dialog', cancel)
    page.get_by_role('button', name='Delete ' + title, exact=True).click()
    assert page.get_by_text(title, exact=True).is_visible()
    dialogs = []
    def confirm(dialog):
        dialogs.append(dialog.message)
        dialog.accept()
    page.once('dialog', confirm)
    with page.expect_response(lambda response: response.request.method == 'DELETE'
            and response.url.endswith('/api/content/dailysynthetic4111')) as pending:
        page.get_by_role('button', name='Delete ' + title, exact=True).click()
    response = pending.value
    body = response.json()
    assert response.status == 200 and body == {'ok': True, 'id': 'dailysynthetic4111',
        'trashed': 2, 'artifactsRemoved': True, 'runnerKicked': False}, body
    observations.append({'action': 'confirmed_delete', 'status': response.status, 'body': body,
        'cache_control': response.headers.get('cache-control')})
    page.get_by_text(title, exact=True).wait_for(state='hidden')
    assert dialogs == ['Delete "' + title + '" and stop its tasks?'], dialogs
    assert not errors, errors
    assert all(row['cache_control'] == 'no-store' for row in observations)
    page.screenshot(path=str(evidence / 'installed-browser-content-disposed.png'), full_page=True)
    context.close()
    browser.close()
effects = fixture('verify')
report = {'status': 'PASS', 'elapsed_seconds': round(time.monotonic() - started, 3),
    'playwright_version': version('playwright'), 'observations': observations,
    'cancelled_delete_preserves_item': True, 'effects': effects, 'page_errors': errors,
    'live_profile_changed': False, 'media_processing_verified': False}
(evidence / 'installed-browser-content-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
