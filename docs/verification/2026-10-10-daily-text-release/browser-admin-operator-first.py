# ABOUTME: Completes actual Hermes browser checks after the T3 desktop preview becomes unavailable.
# ABOUTME: Uses only the synthetic acceptance login and records page and browser diagnostics.
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
report = {'transport': 'Local headless Playwright after explicit T3 preview unavailability',
          'console': [], 'failed_requests': [], 'http_errors': [], 'pages': []}
with sync_playwright() as manager:
    browser = manager.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.on('console', lambda message: report['console'].append({'type': message.type, 'text': message.text}))
    page.on('pageerror', lambda error: report.setdefault('page_errors', []).append(str(error)))
    page.on('requestfailed', lambda request: report['failed_requests'].append({'url': request.url, 'failure': request.failure}))
    page.on('response', lambda response: report['http_errors'].append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
    page.goto('http://127.0.0.1:18819/')
    page.get_by_role('textbox', name='Username').fill('acceptance-owner')
    page.get_by_role('textbox', name='Password').fill('synthetic-application-acceptance-password')
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url('http://127.0.0.1:18819/?profile=default')
    page.get_by_text('Gateway Running', exact=True).wait_for(timeout=20000)
    report['pages'].append({'url': page.url, 'title': page.title(), 'body': page.locator('body').inner_text()})
    page.goto('http://127.0.0.1:18819/lifeos-bridge?profile=default')
    page.wait_for_function("() => !document.body.innerText.includes('Loading plugin settings')", timeout=30000)
    page.wait_for_timeout(2000)
    body = page.locator('body').inner_text()
    assert 'Memory native' in body, body
    assert 'Check: ok' in body, body
    report['pages'].append({'url': page.url, 'title': page.title(), 'body': body})
    page.screenshot(path=str(here/'hermes-plugin-final.png'), full_page=True)
    assert not report.get('page_errors'), report.get('page_errors')
    report['status'] = 'PASS'
    browser.close()
(here/'browser-admin-final.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'status': report['status'], 'pages': len(report['pages']),
                  'http_errors': report['http_errors'], 'failed_requests': report['failed_requests']}, indent=2))
