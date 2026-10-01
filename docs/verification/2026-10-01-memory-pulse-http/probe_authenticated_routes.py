# ABOUTME: Runs protected PULSE owner routes over a real localhost HTTP connection.
# ABOUTME: Records authority and freshness results without recording session credentials.
import json
import socket
import threading
import time

import httpx
import uvicorn
from test_memory_native import OWNER
from test_memory_pulse_auth import MemoryPulseAuthTests


case = MemoryPulseAuthTests()
case.setUp()
server = uvicorn.Server(uvicorn.Config(case.app, log_level='error', lifespan='off'))
listener = socket.socket()
listener.bind(('127.0.0.1', 0))
port = listener.getsockname()[1]
thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
thread.start()
try:
    deadline = time.monotonic() + 10
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError('The synthetic authenticated HTTP server did not start')
        time.sleep(0.01)
    results = {}
    with httpx.Client(base_url=f'http://127.0.0.1:{port}') as client:
        endpoint = case.endpoint
        results['anonymous'] = {view: client.get(endpoint + view).status_code
                               for view in ('snapshot', 'state', 'health', 'runs')}
        assert set(results['anonymous'].values()) == {401}
        login = client.post('/auth/password-login', json={'provider': 'basic',
            'username': 'synthetic-owner', 'password': 'synthetic-password'})
        assert login.status_code == 200, login.text
        results['owner'] = {}
        for view in ('snapshot', 'state', 'health', 'runs'):
            response = client.get(endpoint + view)
            results['owner'][view] = {'status': response.status_code,
                'cache_control': response.headers.get('cache-control'),
                'etag_present': 'etag' in response.headers}
            assert response.status_code == 200, response.text
            assert response.headers.get('cache-control') == 'no-store'
        snapshot = client.get(endpoint + 'snapshot').json()
        assert snapshot['principalMemory']['entries'] == ['RULE: Synthetic authenticated PULSE fact']
        memory = case.fixture.fixture.fixture.fixture.memory
        reference = memory.recall(OWNER, 'Synthetic authenticated PULSE fact')[0]['reference']
        assert memory.forget(OWNER, reference, 'http-pulse-forget')['status'] == 'committed'
        after_forget = client.get(endpoint + 'snapshot')
        results['after_forget'] = {'status': after_forget.status_code,
                                 'count': after_forget.json()['principalMemory']['count']}
        assert after_forget.json()['principalMemory']['entries'] == []
        case.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
        revoked = client.get(endpoint + 'snapshot')
        results['after_binding_removal'] = {'status': revoked.status_code,
                                            'cache_control': revoked.headers.get('cache-control')}
        assert revoked.status_code == 403, revoked.text
        logout = client.post('/auth/logout', follow_redirects=False)
        assert logout.status_code == 302
        results['after_browser_logout'] = client.get(endpoint + 'snapshot').status_code
        assert results['after_browser_logout'] == 401
    print(json.dumps(results, indent=2))
finally:
    server.should_exit = True
    thread.join(timeout=10)
    listener.close()
    case.doCleanups()
    if thread.is_alive():
        raise RuntimeError('The synthetic HTTP server did not stop')
