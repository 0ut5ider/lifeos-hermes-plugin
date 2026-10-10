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
        python, '-I', '-B', stage + '/content_browser_fixture_seventh.py', action], capture_output=True, text=True, timeout=30)
    assert (result.returncode, result.stderr) == (0, ''), result.stdout + result.stderr
    return json.loads(result.stdout)
def binding(action):
    result = subprocess.run(['ssh', 'root@192.168.8.252', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-I', '-B', stage + '/browser_owner_binding_second.py', action], capture_output=True, text=True, timeout=30)
    assert (result.returncode, result.stderr) == (0, ''), result.stdout + result.stderr
    return json.loads(result.stdout)
assert fixture('prepare')['prepared']
print('fixture_prepared', flush=True)
started = time.monotonic()
observations = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    print('browser_launched', flush=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    finished = []
    page.on('requestfinished', lambda request: finished.append({'method': request.method, 'url': request.url}) if '/api/content/dailysynthetic4117' in request.url else None)
    protocol = context.new_cdp_session(page)
    protocol.send('Network.enable')
    requests = {}
    wire_finished = []
    protocol.on('Network.requestWillBeSent', lambda event: requests.update({event['requestId']: event['request']['url']}) if '/api/content/dailysynthetic4117' in event['request']['url'] else None)
    protocol.on('Network.loadingFinished', lambda event: wire_finished.append({'url': requests[event['requestId']], 'encoded_bytes': event['encodedDataLength']}) if event['requestId'] in requests else None)
    page.set_default_timeout(20_000)
    page.set_default_navigation_timeout(20_000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://localhost:18819/login?next=/')
    page.locator('input[name=username]').fill('acceptance-owner')
    page.locator('input[name=password]').fill('synthetic-application-acceptance-password')
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url('http://localhost:18819/')
    print('signed_in', flush=True)
    page.goto('http://localhost:18837/content', wait_until='domcontentloaded')
    title = 'Synthetic browser seventh Content acceptance'
    page.get_by_text(title, exact=True).wait_for(state='visible')
    card = page.locator('div.p-3.mb-2').filter(has=page.get_by_text(title, exact=True))
    page.get_by_text(re.compile('^live$', re.I)).wait_for(state='visible')
    print('board_live', flush=True)
    assert binding('revoke')['status'] == 'PASS'
    try:
        with page.expect_response(lambda response: response.request.method == 'POST'
                and response.url.endswith('/api/content/dailysynthetic4117/run')) as refusal:
            page.get_by_role('button', name='\u25b6 RUN', exact=True).click()
        denied = refusal.value
        assert denied.status == 403, denied.status
        page.get_by_role('alert').filter(has_text='Content action failed. Refresh the page and try again.').wait_for(state='visible')
        assert page.get_by_role('alert').filter(has_text='Content action failed. Refresh the page and try again.').inner_text() == 'Content action failed. Refresh the page and try again.'
        assert binding('check')['status'] == 'PASS'
        observations.append({'action': 'revoked_owner_run', 'status': denied.status,
            'body': denied.json(), 'cache_control': denied.headers.get('cache-control')})
    finally:
        assert binding('restore')['status'] == 'PASS'
    with page.expect_response(lambda response: response.request.method == 'POST'
            and response.url.endswith('/api/content/dailysynthetic4117/run')) as pending:
        page.get_by_role('button', name='\u25b6 RUN', exact=True).click()
    response = pending.value
    print('response_received', flush=True)
    body = response.json()
    assert response.status == 200 and body['requested_run'] == 'regular', body
    observations.append({'action': 'run', 'status': response.status, 'body': body,
        'cache_control': response.headers.get('cache-control')})
    card.get_by_text('RUN QUEUED', exact=True).wait_for(state='visible')
    print('queued_visible', flush=True)
    page.screenshot(path=str(evidence / 'installed-browser-content-seventh-queued.png'), full_page=True)
    print('queued_screenshot', flush=True)
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
            and response.url.endswith('/api/content/dailysynthetic4117')) as pending:
        page.get_by_role('button', name='Delete ' + title, exact=True).click()
    response = pending.value
    print('response_received', flush=True)
    body = response.json()
    assert response.status == 200 and body == {'ok': True, 'id': 'dailysynthetic4117', 'trashed': 2, 'artifactsRemoved': True, 'runnerKicked': False}, body
    observations.append({'action': 'confirmed_delete', 'status': response.status, 'body': body,
        'cache_control': response.headers.get('cache-control')})
    page.get_by_text(title, exact=True).wait_for(state='hidden')
    assert dialogs == ['Delete "' + title + '" and stop its tasks?'], dialogs
    until = time.monotonic() + 20
    while len(finished) < 3 and time.monotonic() < until:
        page.wait_for_timeout(100)
    print(json.dumps({'finished': finished, 'wire_finished': wire_finished}), flush=True)
    assert len(finished) == 3 and len(wire_finished) == 3, (finished, wire_finished)
    assert page.get_by_role('alert').filter(has_text='Content action failed. Refresh the page and try again.').count() == 0
    assert not errors, errors
    assert all(row['cache_control'] == 'no-store' for row in observations)
    page.screenshot(path=str(evidence / 'installed-browser-content-seventh-disposed.png'), full_page=True)
    context.close()
    print('context_closed', flush=True)
    browser.close()
    print('browser_closed', flush=True)
effects = fixture('verify')
report = {'status': 'PASS', 'elapsed_seconds': round(time.monotonic() - started, 3),
    'playwright_version': version('playwright'), 'observations': observations,
    'cancelled_delete_preserves_item': True, 'real_owner_refusal_displayed': True, 'binding_restored': True, 'refusal_leaves_ledger_and_source_unchanged': True, 'effects': effects, 'page_errors': errors, 'finished_requests': finished, 'wire_finished': wire_finished,
    'live_profile_changed': False, 'media_processing_verified': False}
(evidence / 'installed-browser-content-seventh-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
