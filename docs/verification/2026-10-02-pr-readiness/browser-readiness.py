# ABOUTME: Uses a real password session to verify guarded controls and program version restore.
# ABOUTME: Records status receipts and screenshots without credentials or session cookies.
import argparse
import json
from pathlib import Path
import time
import hashlib
import shlex
import subprocess
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
BASE = 'http://192.168.8.212:8921'
PREFIX = '/api/plugins/lifeos-hook-bridge'
LOGIN = Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002/browser-login.json')
parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=('baseline', 'restore', 'update', 'recover'))
args = parser.parse_args()
login = json.loads(LOGIN.read_text())
receipts = []


def audit_state(prefix_length=None):
    code = ('from pathlib import Path; import hashlib,json; '
            'p=Path("/home/lifeos-plugin-install-probe/acceptance-20261002/.config/LIFEOS/USER/MEMORY/OBSERVABILITY/config-changes.jsonl"); '
            'b=p.read_bytes(); print(json.dumps({"size":len(b),"sha256":hashlib.sha256(b).hexdigest(),"inode":p.stat().st_ino,'
            f'"prefix_sha256":hashlib.sha256(b[:{prefix_length!r}]).hexdigest()}}))')
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'outsider@192.168.8.212',
        'sudo -n -u lifeos-plugin-install-probe python3 -c ' + shlex.quote(code)],
        text=True, capture_output=True, timeout=20, check=True)
    return json.loads(result.stdout)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1500, 'height': 1100})
    page.goto(BASE + '/login')
    page.locator('input[name="username"]').fill(login['username'])
    page.locator('input[name="password"]').fill(login['password'])
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url(BASE + '/')
    page.get_by_role('link', name='LifeOS Bridge', exact=False).click()
    endpoint = BASE + PREFIX + '/installation/update'
    if args.phase == 'baseline':
        for path in ('finalize', 'update', 'prepare', 'apply', 'prepare-hermes', 'apply-hermes', 'restore-hermes', 'update/restore', 'update/recover'):
            url = BASE + PREFIX + '/installation/' + path
            for options, expected in (({'headers': {'Origin': 'http://192.168.8.212:8999'}}, 403),
                                      ({'data': {'installed': 'override'}}, 400)):
                result = page.request.post(url, **options)
                receipts.append({'action': path, 'request': 'other-origin' if expected == 403 else 'body',
                                 'status': result.status})
                assert result.status == expected, (path, result.status, result.text())
        source = '/home/lifeos-plugin-install-probe/acceptance-20261002/.local/share/lifeos-bridge/lifeos-candidate/LifeOS/install'
        preview = page.request.post(BASE + PREFIX + '/version-drift/preview', data={'source': source})
        assert preview.status == 200, preview.text()
        renewed = page.request.post(BASE + PREFIX + '/version-drift', data={
            'source': source, 'fingerprint': preview.json()['fingerprint'], 'renew': True})
        assert renewed.status == 200, renewed.text()
        receipts.append({'reviewed_change': 'ARCHITECTURE_SUMMARY.md generated timestamp only',
                         'baseline': renewed.json()})
    else:
        if args.phase == 'restore':
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                state = page.request.get(endpoint).json()
                receipts.append(state)
                if state['state'] not in {'queued', 'preparing', 'applying'}:
                    break
                page.wait_for_timeout(2000)
            assert state['state'] == 'applied', state
            page.reload()
            button = page.get_by_role('button', name='Restore previous LifeOS version', exact=True)
            request_endpoint = endpoint + '/restore'
            terminal = 'rolled_back'
        elif args.phase == 'update':
            button = page.get_by_role('button', name='Apply prepared LifeOS update', exact=True)
            request_endpoint = endpoint
            terminal = 'applied'
        else:
            button = page.get_by_role('button', name='Restore interrupted mount', exact=True)
            request_endpoint = BASE + PREFIX + '/installation/mount/recover'
            terminal = 'rolled_back'
        button.wait_for(timeout=20000)
        if args.phase == 'restore':
            receipts.append({'external_audit_before': audit_state()})
        deadline = time.monotonic() + 30
        while True:
            with page.expect_response(lambda response: response.url == request_endpoint and response.request.method == 'POST', timeout=120000) as pending:
                button.click()
            response = pending.value
            receipts.append({'request_status': response.status, 'result': response.json()})
            if response.status != 409 or response.json().get('detail') != 'Another installation operation is running' or time.monotonic() > deadline:
                break
            page.wait_for_timeout(1000)
        assert response.status == 200, receipts[-1]
        if args.phase != 'recover':
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                state = page.request.get(endpoint).json()
                receipts.append(state)
                if state['state'] not in {'queued', 'preparing', 'applying', 'restoring', 'recovering'}:
                    break
                page.wait_for_timeout(2000)
            assert state['state'] == terminal, state
            if args.phase == 'restore':
                audit_before = next(record['external_audit_before'] for record in receipts if 'external_audit_before' in record)
                audit_after = audit_state(audit_before['size'])
                receipts.append({'external_audit_after': audit_after})
                assert audit_before['sha256'] == audit_after['prefix_sha256'], (audit_before, audit_after)
                assert audit_before['inode'] == audit_after['inode'] and audit_after['size'] >= audit_before['size']
        else:
            assert response.json()['state'] == terminal, response.json()
        page.reload()
        page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / ('browser-' + args.phase + '.png')), full_page=True)
    (OUT / ('browser-' + args.phase + '.json')).write_text(json.dumps(receipts, indent=2) + '\n')
    print(json.dumps({'phase': args.phase, 'verified': True, 'checks': len(receipts)}))
    browser.close()
