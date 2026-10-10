# ABOUTME: Verifies real Chromium rendering and authenticated native requests in the isolated acceptance dashboard.
# ABOUTME: Retains synthetic page observations without reading live profile data or transport credentials.
from importlib.metadata import version
import json
from pathlib import Path
import re
import time
from playwright.sync_api import sync_playwright

evidence = Path(__file__).resolve().parent
observations = []
started = time.monotonic()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.goto('http://localhost:18819/login?next=/')
    page.locator('input[name=username]').fill('acceptance-owner')
    page.locator('input[name=password]').fill('synthetic-application-acceptance-password')
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url('http://localhost:18819/')
    assert '/login' not in page.url
    routes = [('/', '/api/life/home', 200), ('/life', '/api/life/home', 200),
        ('/telos', '/api/telos/freshness/summary', 200), ('/content', '/api/content', 200),
        ('/health', '/api/life/health', 200), ('/finances', '/api/life/finances', 200),
        ('/business', '/api/life/business', 200), ('/growth', '/api/life/growth', 200),
        ('/local', '/api/local-intelligence', 404), ('/gear', '/api/assets', 200),
        ('/books', '/api/books', 200), ('/atlas', '/api/atlas', 200),
        ('/memory', '/api/memory', 200)]
    for path, api, status in routes:
        console_errors = []
        page_errors = []
        def console_observer(message):
            if message.type == 'error':
                console_errors.append(message.text)
        def error_observer(error):
            page_errors.append(str(error))
        page.on('console', console_observer)
        page.on('pageerror', error_observer)
        # Network completion and visible body state precede observation. No endpoint is mocked.
        if path == '/content':
            page.goto('http://localhost:18837' + path, wait_until='domcontentloaded')
            page.get_by_text(re.compile('^live$', re.I)).wait_for(state='visible')
        elif path == '/local':
            page.goto('http://localhost:18837' + path, wait_until='domcontentloaded')
            page.get_by_text('No digest generated yet.', exact=True).wait_for(state='visible')
        else:
            page.goto('http://localhost:18837' + path, wait_until='networkidle')
        page.locator('body').wait_for(state='visible')
        response = context.request.get('http://localhost:18837' + api)
        body = page.locator('body').inner_text()
        observation = {'path': path, 'url': page.url, 'title': page.title(), 'body': body,
            'api': api, 'api_status': response.status,
            'cache_control': response.headers.get('cache-control'),
            'console_errors': list(console_errors), 'page_errors': list(page_errors)}
        observations.append(observation)
        (evidence / 'installed-browser-pages-fourth-progress.json').write_text(json.dumps(observations, indent=2) + '\n')
        assert response.status == status, observation
        assert page.title().startswith('Pulse |'), observation
        assert 'PULSE' in body and 'Sign in' not in body, observation
        assert not page_errors, observation
        if path != '/growth':
            assert response.headers.get('cache-control') == 'no-store', observation
        page.screenshot(path=str(evidence / ('installed-browser-fourth-' + (path.strip('/') or 'home') + '.png')), full_page=True)
        page.remove_listener('console', console_observer)
        page.remove_listener('pageerror', error_observer)
    context.close()
    browser.close()
report = {'status': 'PASS', 'playwright_version': version('playwright'),
    'elapsed_seconds': round(time.monotonic() - started, 3), 'pages': observations,
    'actual_chromium_rendering': True, 'media_processing_verified': False,
    'dashboard_actions_verified': False, 'live_profile_changed': False}
(evidence / 'installed-browser-pages-fourth-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'page_count': len(observations),
    'elapsed_seconds': report['elapsed_seconds'], 'playwright_version': report['playwright_version']}, indent=2))
