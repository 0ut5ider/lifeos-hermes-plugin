# ABOUTME: Saves the activated daily guest to PBS after a governed writer drain.
# ABOUTME: Resumes the original services and verifies authenticated access after restart.
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

os.umask(0o077)
here = Path('/root/lifeos-daily-install/active-backup')
here.mkdir(mode=0o700, exist_ok=True)
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
operations = []
guest_program = '''
import http.cookiejar, importlib, json, os, sys, time, urllib.request
from pathlib import Path
home = Path('/home/lifeos-hermes')
os.environ.update(json.loads((home/'deployment/2026-10-11/environment.json').read_text()),
    XDG_RUNTIME_DIR='/run/user/1000', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
profile = home/'.hermes'
sys.path[:0] = [str(profile/'plugins'),str(home/'runtime/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.'+name)
configuration = module('memory_service').MemoryConfiguration(profile/'lifeos-memory.json')
selected = configuration.load()
assert selected['ownership_enabled'] and not selected['sharing_enabled']
services = module('profile_services').ProfileServices(profile, Path(selected['root']))
if sys.argv[1] == 'drain':
    assert not json.loads((profile/'runtime/active_sessions.json').read_text())['entries']
    services.drain(signature=services.preview()['signature'])
    print(json.dumps(services.verify_stopped()))
else:
    resumed = services.resume()
    from dotenv import dotenv_values
    audience = module('discord_audience')
    api = audience.DiscordAPI(dotenv_values(profile/'.env')['DISCORD_BOT_TOKEN'])
    metadata = {'HERMES_SESSION_PLATFORM':'discord','HERMES_SESSION_CHAT_ID':'1558870196784205927',
        'HERMES_SESSION_CHAT_TYPE':'group','HERMES_SESSION_SCOPE_ID':'1553540018302099486',
        'HERMES_SESSION_USER_ID':'708089927468056648'}
    assert audience.resolve_audience(selected,metadata,api=api) is not None
    credentials = json.loads((home/'install-input/dashboard-access.json').read_text())
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    deadline = time.monotonic()+60
    while True:
        try:
            request = urllib.request.Request('http://127.0.0.1:18819/auth/password-login',
                data=json.dumps({'provider':'basic',**credentials}).encode(),
                headers={'Content-Type':'application/json'})
            with client.open(request,timeout=10) as response:
                assert response.status == 200
                response.read()
            for port,path in [(18819,'/api/plugins/lifeos-hook-bridge/memory'),(18837,'/api/memory')]:
                with client.open('http://127.0.0.1:'+str(port)+path,timeout=15) as response:
                    assert response.status == 200
                    response.read()
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    print(json.dumps({'status':'PASS','services':resumed,'private_audience_verified':True,
        'authenticated_dashboard':200,'authenticated_pulse_memory':200,
        'ownership_enabled':True,'sharing_enabled':False}))
'''


def run(args, label, *, source=None):
    started = time.monotonic()
    result = subprocess.run(args, input=source, capture_output=True, text=True,
        timeout=1800, umask=0o022 if args[0] == 'vzdump' else -1)
    (here / (label + '.stdout')).write_text(result.stdout)
    (here / (label + '.stderr')).write_text(result.stderr)
    operations.append({'label': label, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3)})
    print(json.dumps(operations[-1]), flush=True)
    assert result.returncode == 0, label + ': ' + result.stdout[-2000:] + result.stderr[-2000:]
    return result.stdout


def guest(action):
    return run(['pct', 'exec', '102', '--', 'runuser', '-u', 'lifeos-hermes', '--',
        python, '-B', '-', action], action, source=guest_program)


status = 'FAIL'
archive = None
drained = False
drain_attempted = False
try:
    drain_attempted = True
    guest('drain')
    drained = True
    run(['pct', 'shutdown', '102', '--timeout', '90'], 'shutdown')
    run(['vzdump', '102', '--storage', 'PBS-01', '--mode', 'stop', '--notes-template',
        'LifeOS 0.2.0 activated Cerebo daily configuration'], 'backup')
    content = json.loads(run(['pvesh', 'get', '/nodes/pve-tr1950x/storage/PBS-01/content',
        '--content', 'backup', '--vmid', '102', '--output-format', 'json'], 'archives'))
    archive = max(content, key=lambda row: row['ctime'])['volid']
    assert archive.startswith('PBS-01:backup/ct/102/')
    target = '/nodes/pve-tr1950x/storage/PBS-01/content/' + archive
    run(['pvesh', 'set', target, '--protected', '1'], 'protect')
    attributes = json.loads(run(['pvesh', 'get', target, '--output-format', 'json'], 'attributes'))
    assert attributes['protected'] == 1
    status = 'BACKUP_COMPLETE'
except BaseException:
    (here / 'failure.log').write_text(traceback.format_exc())
    raise
finally:
    try:
        state = subprocess.check_output(['pct', 'status', '102'], text=True)
        if 'stopped' in state:
            run(['pct', 'start', '102'], 'start')
        if drain_attempted:
            deadline = time.monotonic() + 60
            while True:
                probe = subprocess.run(['pct', 'exec', '102', '--', 'test', '-S',
                    '/run/user/1000/bus'], capture_output=True)
                if probe.returncode == 0:
                    break
                assert time.monotonic() < deadline, 'The owner service manager does not start'
                time.sleep(1)
            resumed = json.loads(guest('resume'))
            assert resumed['status'] == 'PASS'
            if status == 'BACKUP_COMPLETE':
                status = 'PASS'
    finally:
        report = {'status': status, 'archive': archive, 'guest': 102,
            'writer_drain_verified': drained, 'new_archive_restore_tested': False,
            'operations': operations}
        (here / 'active-backup.json').write_text(json.dumps(report, indent=2) + '\n')
        (here / '.done').write_text('0\n' if status == 'PASS' else '1\n')
