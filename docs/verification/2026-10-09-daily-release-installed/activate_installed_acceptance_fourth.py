# ABOUTME: Activates ownership through actual backup and three-service draining in the isolated profile.
# ABOUTME: Records authenticated application responses and leaves the production profile outside the operation.
import importlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error
import http.cookiejar

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile = Path(prepared['profile'])
installed = Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(installed.parent), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    PYTHONPATH=str(stage / 'package/hermes'), TZ='America/Toronto',
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus',
    PULSE_PORT='18837', PULSE_URL='http://127.0.0.1:18837')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, installed, units=units)
setup = module('ownership_setup').OwnershipSetup(configuration, units=units)
account = 'dashboard:basic:acceptance-owner'
before = services.preview()
plan = setup.prepare(stage / 'application-ownership-backup-fourth', account=account)
(stage / 'application-ownership-review-fourth.json').write_text(json.dumps(plan, indent=2) + '\n')
receipt = setup.apply(plan['signature'], account=account)
if receipt['state'] != 'configured' or not configuration.load()['ownership_enabled']:
    raise RuntimeError('The isolated ownership operation does not reach its configured state')
(stage / 'application-ownership-configured-fourth.json').write_text(json.dumps(receipt, indent=2) + '\n')
cookie = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(cookie))
def request(url, data=None):
    headers = {'Content-Type': 'application/json'} if data is not None else {}
    wire = None if data is None else json.dumps(data).encode()
    try:
        response = client.open(urllib.request.Request(url, data=wire, headers=headers), timeout=45)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise RuntimeError('The application response exceeds its acceptance limit')
        return response.status, raw, {key.lower(): value for key, value in response.headers.items()}
login = 'http://127.0.0.1:18819/auth/password-login'
for attempt in range(30):
    try:
        status, raw, headers = request(login, {'provider': 'basic', 'username': 'acceptance-owner',
            'password': 'synthetic-application-acceptance-password'})
        break
    except (OSError, urllib.error.URLError):
        time.sleep(1)
else:
    raise RuntimeError('The restarted actual dashboard does not accept a login request')
if status != 200:
    raise RuntimeError('The actual dashboard refuses the synthetic owner login: ' + str(status))
observations = []
for path in ('/api/memory', '/api/telos/freshness/summary', '/api/conduit/status', '/healthz'):
    status, raw, headers = request('http://127.0.0.1:18837' + path)
    observations.append({'path': path, 'status': status, 'body': json.loads(raw),
        'cache_control': headers.get('cache-control')})
    (stage / 'application-activation-observation-fourth-progress.json').write_text(json.dumps(observations, indent=2) + '\n')
    if status != 200:
        raise RuntimeError('The admitted application route refuses ' + path + ': ' + str(status))
report = {'status': 'PASS', 'ownership_receipt': receipt, 'service_state': services.status(),
    'observations': observations, 'transport_credentials_loaded': False, 'live_profile_changed': False,
    'browser_verified': False, 'scheduled_execution_verified': False, 'owner_turn_verified': False}
(stage / 'application-activation-observation-fourth.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
