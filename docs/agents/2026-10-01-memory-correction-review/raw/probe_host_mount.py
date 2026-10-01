# ABOUTME: Checks plugin header installation during real isolated Hermes app assembly.
# ABOUTME: Runs the owned public dashboard source with synthetic facts and a private profile.
import json
from pathlib import Path

from fastapi.testclient import TestClient
from test_memory_pulse_auth import MemoryPulseAuthTests


case = MemoryPulseAuthTests()
case.setUp()
try:
    plugins = case.profile / 'plugins'
    plugins.mkdir()
    (plugins / 'lifeos-hook-bridge').symlink_to(Path(__file__).resolve().parents[3] / 'lifeos_hook_bridge')
    (case.profile / 'config.yaml').write_text('plugins:\n  enabled: [lifeos-hook-bridge]\n'
                                             'memory:\n  memory_enabled: false\n  user_profile_enabled: false\n')
    from hermes_cli.web_server import app
    assert getattr(app.state, 'lifeos_memory_cache_headers', False), 'The real host did not install plugin response headers'
    app.state.auth_required = True
    results = {'middleware_installed': True}
    with TestClient(app, base_url='http://127.0.0.1') as client:
        response = client.get(case.endpoint + 'snapshot')
        results['anonymous'] = {'status': response.status_code, 'cache_control': response.headers.get('cache-control')}
        assert response.status_code == 401, response.text
        assert response.headers.get('cache-control') == 'no-store'
        response = client.post('/auth/password-login', json={'provider': 'basic',
            'username': 'synthetic-owner', 'password': 'synthetic-password'})
        assert response.status_code == 200, response.text
        response = client.get(case.endpoint + 'snapshot')
        results['owner'] = {'status': response.status_code, 'cache_control': response.headers.get('cache-control')}
        assert response.status_code == 200, response.text
        assert response.json()['principalMemory']['count'] == 1
        for label, response in (('invalid_view', client.get(case.endpoint + 'graph')),
                                 ('invalid_method', client.post(case.endpoint + 'snapshot', json={}))):
            results[label] = {'status': response.status_code, 'cache_control': response.headers.get('cache-control')}
            assert response.headers.get('cache-control') == 'no-store'
    print(json.dumps(results, indent=2))
finally:
    case.doCleanups()
