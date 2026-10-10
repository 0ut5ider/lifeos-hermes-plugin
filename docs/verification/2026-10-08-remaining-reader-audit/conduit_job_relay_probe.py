# ABOUTME: Observes actual dashboard refusal reasons while a native Conduit owner job runs.
# ABOUTME: Retains synthetic HTTP statuses and file effects without replacing a handler result.
import sys
import json
import time
from pathlib import Path
import httpx
from test_memory_conduit_jobs import MemoryConduitJobRelayTests

fixture = MemoryConduitJobRelayTests()
fixture.setUp()
errors = []
report = {'responses': [], 'refusals': errors}
observers = []
try:
    fixture.fixture.login()
    prepared = fixture.fixture.client.post('/api/plugins/lifeos-hook-bridge/memory/conduit_job')
    report['preparation'] = {'status': prepared.status_code, 'body': prepared.json()}
    classes = {getattr(module, 'MemoryPreferences') for name, module in list(sys.modules.items())
        if name.endswith('memory_preferences') and hasattr(module, 'MemoryPreferences')}
    report['owner_classes'] = [owner_class.__module__ for owner_class in classes]
    for owner_class in classes:
        original = owner_class.life_response
        def observed(preferences, *arguments, _original=original, **keywords):
            try: return _original(preferences, *arguments, **keywords)
            except Exception as error:
                errors.append({'type': type(error).__name__, 'message': str(error)})
                raise
        owner_class.life_response = observed
        observers.append((owner_class, original))
    with httpx.Client(timeout=30) as client:
        fixture.login(client)
        response = client.post(fixture.native + '/api/conduit/insight/build')
        report['start'] = {'status': response.status_code, 'body': response.json()}
        for _ in range(15):
            response = client.get(fixture.native + '/api/conduit/insight')
            report['responses'].append({'status': response.status_code, 'body': response.json()})
            if response.status_code == 200 and not response.json()['building']: break
            time.sleep(0.2)
    report['artifacts'] = [str(path.relative_to(fixture.root)) for path in
        (fixture.root / 'LIFEOS/USER/CONDUIT').rglob('*.json')]
    print(json.dumps(report, indent=2))
finally:
    for owner_class, original in observers: owner_class.life_response = original
    fixture.doCleanups()
