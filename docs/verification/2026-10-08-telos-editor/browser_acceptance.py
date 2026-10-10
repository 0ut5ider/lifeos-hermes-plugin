# ABOUTME: Checks the actual TELOS editor UI against real disposable authenticated native services.
# ABOUTME: Captures successful saves, conflict preservation, and fresh-reference recovery without mocked requests.
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

folder = Path(__file__).parent
endpoint = json.loads((folder / 'browser-endpoint.json').read_text())
source = Path(endpoint['source'])
requests = []
responses = []
console = []
with sync_playwright() as runtime:
    browser = runtime.chromium.launch(headless=True)
    try:
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        page.on('console', lambda message: console.append({'type': message.type, 'text': message.text}))
        page.on('request', lambda request: requests.append({'method': request.method, 'url': request.url,
            'body': request.post_data_json if request.method == 'PUT' else None}))
        page.on('response', lambda response: responses.append({'method': response.request.method,
            'url': response.url, 'status': response.status}))
        page.goto(endpoint['url'])
        page.get_by_text('An authenticated Hermes session is required', exact=True).wait_for()
        assert source.read_text() == '# SyntheticEditableTelosGoal\nSynthetic current goal\n'
        login = context.request.post(endpoint['url'] + '/auth/password-login', data={
            'provider': 'basic', 'username': 'synthetic-owner', 'password': 'synthetic-password'})
        assert login.status == 200, login.text()
        login.json()
        page.reload()
        page.get_by_text('Ready', exact=True).wait_for()
        assert page.get_by_role('textbox').input_value() == source.read_text()
        page.get_by_role('textbox').fill('# SyntheticBrowserSavedTelosGoal\n')
        page.get_by_role('button', name='Save', exact=True).click()
        page.get_by_text('Saved count: 1', exact=True).wait_for()
        assert source.read_text() == '# SyntheticBrowserSavedTelosGoal\n'
        assert source.stat().st_mode & 0o777 == 0o600
        page.get_by_role('button', name='Open GOALS', exact=True).click()
        page.get_by_text('Loading...', exact=True).wait_for()
        page.get_by_text('Ready', exact=True).wait_for()
        page.get_by_role('textbox').fill('# SyntheticStaleBrowserSave\n')
        source.write_text('# SyntheticConcurrentBrowserOwnerEdit\n')
        before = source.read_bytes(), source.stat().st_mtime_ns
        page.get_by_role('button', name='Save', exact=True).click()
        page.get_by_text('The TELOS save conflicts with the current source or policy. Open the file again.', exact=True).wait_for()
        assert (source.read_bytes(), source.stat().st_mtime_ns) == before
        assert page.get_by_role('textbox').input_value() == '# SyntheticStaleBrowserSave\n'
        page.screenshot(path=str(folder / 'browser-conflict.png'))
        page.on('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Cancel', exact=True).click()
        page.get_by_role('button', name='Open GOALS', exact=True).click()
        page.get_by_text('Loading...', exact=True).wait_for()
        page.get_by_text('Ready', exact=True).wait_for()
        assert page.get_by_role('textbox').input_value() == '# SyntheticConcurrentBrowserOwnerEdit\n'
        page.get_by_role('textbox').fill('# SyntheticRecoveredBrowserSave\n')
        page.get_by_role('button', name='Save', exact=True).click()
        page.get_by_text('Saved count: 2', exact=True).wait_for()
        assert source.read_text() == '# SyntheticRecoveredBrowserSave\n'
        assert source.stat().st_mode & 0o777 == 0o600
        assert [entry['status'] for entry in responses if entry['method'] == 'PUT'] == [200, 409, 200]
        edits = [entry['body'] for entry in requests if entry['method'] == 'PUT']
        assert all(set(edit) == {'name', 'content', 'reference', 'request_id'} for edit in edits)
        assert all(edit['name'] == 'GOALS.md' and len(edit['reference']) == 64 for edit in edits)
        errors = [entry['text'] for entry in console if entry['type'] == 'error']
        assert len(errors) == 2 and all('401' in text or '409' in text for text in errors), errors
        result = {'checks': ['anonymous refusal', 'current owner read', 'UI private save',
            'later edit preservation', 'conflict displayed with unsaved text retained', 'fresh reference recovery'],
            'requests': requests, 'responses': responses, 'console': console,
            'final_source': source.read_text(), 'final_mode': oct(source.stat().st_mode & 0o777)}
        (folder / 'browser-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
        print('PASS: actual editor save, conflict preservation, and fresh-reference recovery')
    finally:
        (folder / 'browser-observation.json').write_text(json.dumps({'requests': requests, 'responses': responses, 'console': console, 'visible_text': page.locator('body').inner_text(), 'source': source.read_text()}, indent=2) + '\n')
        browser.close()
