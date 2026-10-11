# ABOUTME: Activates daily memory through the installed ownership backup and writer-drain workflow.
# ABOUTME: Rechecks the actual private Discord audience and authenticated dashboard before publication.
import http.cookiejar
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import urllib.request


home = Path('/home/lifeos-hermes')
evidence = home / 'deployment/2026-10-11'
os.umask(0o077)
environment = json.loads((evidence / 'environment.json').read_text())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/1000',
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
profile = Path(environment['HERMES_HOME'])
sys.path[:0] = [str(profile / 'plugins'), environment['PYTHONPATH']]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)


def main():
    from dotenv import dotenv_values
    configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
    selected = configuration.load()
    assert not selected['ownership_enabled'] and not selected['sharing_enabled']
    assert json.loads((evidence / 'discord-inbound.json').read_text())['status'] == 'PASS'
    assert not json.loads((profile / 'runtime/active_sessions.json').read_text())['entries']
    channel = '1558870196784205927'
    owner = '708089927468056648'
    metadata = {'HERMES_SESSION_PLATFORM': 'discord', 'HERMES_SESSION_CHAT_ID': channel,
        'HERMES_SESSION_CHAT_TYPE': 'group', 'HERMES_SESSION_SCOPE_ID': '1553540018302099486',
        'HERMES_SESSION_USER_ID': owner}
    audience = module('discord_audience')
    api = audience.DiscordAPI(dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN'])
    assert audience.resolve_audience(selected, metadata, api=api) == audience.ChannelAudience(
        channel, owner, selected['principal'])
    credentials = json.loads((home / 'install-input/dashboard-access.json').read_text())
    assert credentials['username'] == 'adrian'
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def login():
        request = urllib.request.Request('http://127.0.0.1:18819/auth/password-login',
            data=json.dumps({'provider': 'basic', **credentials}).encode(),
            headers={'Content-Type': 'application/json'})
        with client.open(request, timeout=15) as response:
            assert response.status == 200
            response.read()

    login()
    setup = module('ownership_setup').OwnershipSetup(configuration)
    account = 'dashboard:basic:adrian'
    plan = setup.prepare(evidence / 'daily-ownership-profile-backup', account=account)
    (evidence / 'daily-ownership-review.json').write_text(json.dumps(plan, indent=2) + '\n')
    assert plan['state'] == 'ready'
    receipt = setup.apply(plan['signature'], account=account)
    assert receipt['state'] == 'configured'
    selected = configuration.load()
    assert selected['ownership_enabled'] and not selected['sharing_enabled']
    assert audience.resolve_audience(selected, metadata, api=api) is not None
    deadline = time.monotonic() + 60
    while True:
        try:
            login()
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    with client.open('http://127.0.0.1:18819/api/plugins/lifeos-hook-bridge/memory', timeout=30) as response:
        assert response.status == 200
        response.read()
    memory = module('memory_access').NativeMemory(Path(selected['root']))
    with memory._transaction() as connection:
        active = connection.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0]
    assert active == 0
    report = {'status': 'PASS', 'ownership_receipt': receipt,
        'ownership_enabled': True, 'sharing_enabled': False, 'active_facts': active,
        'private_discord_audience_verified': True, 'authenticated_dashboard_status': 200,
        'service_state': setup.status(account=account), 'discord_memory_turn_verified': False,
        'pulse_started': False}
    (evidence / 'daily-ownership-activation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


try:
    main()
except BaseException:
    traceback.print_exc()
    (evidence / 'daily-ownership-activation.done').write_text('1\n')
    raise
else:
    (evidence / 'daily-ownership-activation.done').write_text('0\n')
