# ABOUTME: Backs up and reconstructs the actual synthetic installed acceptance profile.
# ABOUTME: Verifies retained native references and SQLite history while leaving live development services unchanged.
from contextlib import closing
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    PYTHONPATH=str(stage / 'package/hermes'), TZ='America/Toronto',
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
account = 'dashboard:basic:acceptance-owner'
scope = module('memory_preferences').MemoryPreferences._owner_scope(configuration.load())
memory = module('memory_access').NativeMemory(root, profile=profile)
reference = {'id': '4da70def445b4b92b240c7123553a0dd', 'revision': 1}
fact_before = memory.get(scope, reference)
assert fact_before['content'] == 'Synthetic daily acceptance verification code is D252-TEXT-1010.'
def history(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        return {'sessions': connection.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],
            'messages': connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0]}
before_history = history(profile / 'state.db')
configuration_before = (profile / 'lifeos-memory.json').read_bytes()
code_before = (profile / 'config.yaml').read_bytes()
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
resumed = False
try:
    started = time.monotonic()
    backup = module('profile_backup').create(configuration, stage / 'release-application-tested-profile-backup', account=account)
    assert backup['status'] == 'committed'
    manifest = module('profile_backup').inspect(configuration, Path(backup['snapshot']), backup['signature'], account=account)
    recovery = module('profile_backup_recovery').recover(configuration, Path(backup['snapshot']),
        backup['signature'], stage / 'release-application-tested-profile-recovery', account=account)
    assert recovery['status'] == 'recovered' and not recovery['ownership_enabled'] and not recovery['sharing_enabled']
    recovered_profile, recovered_root = Path(recovery['profile']), Path(recovery['root'])
    candidate = module('memory_service').MemoryConfiguration(recovered_profile / 'lifeos-memory.json').load()
    assert not candidate['ownership_enabled'] and not candidate['sharing_enabled']
    candidate_scope = module('memory_preferences').MemoryPreferences._owner_scope(candidate)
    recovered_memory = module('memory_access').NativeMemory(recovered_root, profile=recovered_profile)
    recovered_fact = recovered_memory.get(candidate_scope, reference)
    assert recovered_fact['content'] == fact_before['content']
    assert recovered_fact['reference'] == fact_before['reference']
    recovered_history = history(recovered_profile / 'state.db')
    assert recovered_history == before_history
    connector = json.loads((recovered_root / 'LIFEOS/USER/CONFIG/memory-access.json').read_text())
    assert connector['command'][-1] == str(recovered_profile / 'lifeos-memory.json')
    assert (profile / 'lifeos-memory.json').read_bytes() == configuration_before
    assert (profile / 'config.yaml').read_bytes() == code_before
    assert memory.get(scope, reference)['content'] == fact_before['content']
    assert history(profile / 'state.db') == before_history
    recovery_seconds = round(time.monotonic() - started, 3)
    services.resume()
    resumed = True
    report = {'status': 'PASS', 'backup': backup, 'recovery': recovery,
        'elapsed_seconds': recovery_seconds, 'reference': reference,
        'history_before': before_history, 'history_recovered': recovered_history,
        'backup_file_count': len(manifest['files']),
        'configuration_sha256': hashlib.sha256(configuration_before).hexdigest(),
        'source_preserved': True, 'candidate_ownership_disabled': True,
        'candidate_services_started': False, 'rebound_connector_verified': True,
        'source_service_state': services.status(), 'synthetic_data_only': True,
        'live_profile_changed': False, 'offserver_restore_verified': False}
    (stage / 'release-installed-profile-recovery-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
finally:
    if not resumed:
        services.resume()
