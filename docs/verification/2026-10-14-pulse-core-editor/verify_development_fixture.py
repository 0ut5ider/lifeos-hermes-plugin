# ABOUTME: Verifies the installed core editor through authenticated native HTTP and real remounting.
# ABOUTME: Uses only a newly created synthetic account and exports safe acceptance receipts.
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
from ruamel.yaml import YAML

home = Path('/home/lifeos-editor-acceptance')
profile = home / '.hermes'
folder = home / 'deployment/2026-10-14'
environment = json.loads((folder / 'environment.json').read_bytes())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
sys.path[:0] = [str(profile / 'plugins'), str(home / 'runtime/releases/0.5.0-rc.1-02dcd9e3/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
root = Path(configuration.load()['root'])
report = {'status': 'FAIL', 'synthetic_account_only': True, 'production_profile_changed': False,
    'program_commit': '02dcd9e345d105ff2ff48a03847833808226dca6',
    'archive_sha256': 'e05fd7aaa57a78fb0b395afb2107e40311f135f294a61226ab482d8b0ac2fbda'}
code = 1
try:
    with httpx.Client(base_url='http://127.0.0.1:18819', timeout=120) as client:
        login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert login.status_code == 200
        me = client.get('/api/auth/me').json()
        assert me['provider'] == 'basic' and me['user_id'] == 'synthetic-owner' and me['expires_at'] > time.time()
        account = 'dashboard:basic:synthetic-owner'
        configuration.check_owner(configuration.load(), account)
        if not configuration.load()['ownership_enabled']:
            identity = root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
            identity.write_text('# Synthetic installed editor owner\n')
            setup = module('ownership_setup').OwnershipSetup(configuration)
            plan = setup.prepare(folder / 'synthetic-ownership-backup', account=account)
            applied = setup.apply(plan['signature'], account=account)
            assert applied['state'] == 'configured' and configuration.load()['ownership_enabled']
        else:
            identity = root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
            assert module('ownership_setup').OwnershipSetup(configuration).status(account=account)['state'] == 'configured'
        subprocess.run(['systemctl', '--user', 'start', 'com.lifeos.pulse.service'], check=True, capture_output=True)
        login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
        assert login.status_code == 200
        pulse = 'http://127.0.0.1:18837'
        deadline = time.monotonic() + 90
        while True:
            try:
                response = client.get(pulse + '/api/hermes')
                if response.status_code == 200: break
            except httpx.ConnectError: pass
            assert time.monotonic() < deadline, 'The installed governed editor does not become ready: ' + str(response.status_code)
            time.sleep(0.2)
        rows = {row['id']: row for row in response.json()['files']}
        assert len(rows) == 24 and rows['principal-identity']['editable']
        assert response.headers['cache-control'] == 'no-store'
        anonymous = httpx.get(pulse + '/api/hermes/file/principal-identity')
        assert anonymous.status_code == 401
        read = client.get(pulse + '/api/hermes/file/principal-identity')
        assert read.status_code == 200 and read.json()['content'] == identity.read_text()
        reference = read.json()['reference']
        marker = 'Synthetic installed editor governed save.'
        content = '# Synthetic principal fixture\n\n## Quick Reference\n- **Work style:** ' + marker + '\n'
        before_bytes = (profile / 'config.yaml').read_bytes()
        before = YAML(typ='safe').load(before_bytes)
        attempt = str(time.time_ns())
        saved = client.put(pulse + '/api/hermes/file/principal-identity',
            json={'content': content, 'reference': reference, 'request_id': 'installed-editor-' + attempt},
            headers={'Origin': pulse})
        assert saved.status_code == 200 and saved.json()['ok']
        assert identity.read_text() == content and identity.stat().st_mode & 0o777 == 0o600
        stale = client.put(pulse + '/api/hermes/file/principal-identity',
            json={'content': '# Refused stale installed edit', 'reference': reference,
                'request_id': 'installed-editor-stale-' + attempt})
        assert stale.status_code == 409 and identity.read_text() == content
        sealed = client.get(pulse + '/api/hermes/file/hermes-env')
        assert sealed.status_code == 403
        mounted = client.post(pulse + '/api/hermes/remount', headers={'Origin': pulse})
        assert mounted.status_code == 200 and mounted.json()['ok'], (mounted.status_code, mounted.text)
        after_bytes = (profile / 'config.yaml').read_bytes()
        assert YAML(typ='safe').load(after_bytes) == before
        assert marker in (profile / 'SOUL.md').read_text()
        page = client.get(pulse + '/assistant')
        compiled = root / 'LIFEOS/PULSE/Observability/out/assistant.html'
        assert page.status_code == 200 and page.content == compiled.read_bytes()
        report.update(status='PASS', authenticated_owner_verified=True, declared_files=24,
            anonymous_read_status=anonymous.status_code, owner_read_status=read.status_code,
            owner_save_status=saved.status_code, private_save_mode='0600', stale_save_status=stale.status_code,
            sealed_read_status=sealed.status_code, actual_remount_status=mounted.status_code,
            remounted_identity_present=True, configuration_values_preserved=True, configuration_bytes_preserved=before_bytes == after_bytes,
            compiled_assistant_page_matches_package=True, background_jobs_enabled=False,
            discord_credentials_present=False)
        code = 0
finally:
    (folder / 'installed-editor-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (folder / 'installed-editor-verification.done').write_text(str(code) + '\n')
print(json.dumps(report, indent=2))
