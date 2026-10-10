# ABOUTME: Reconstructs the synthetic tested profile from files extracted from the completed PBS archive.
# ABOUTME: Verifies signed copies, native references, and conversation history without starting recovered services.
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

def history(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        return {'sessions': connection.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],
            'messages': connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0]}

configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
configuration_before = configuration.path.read_bytes()
yaml_before = (profile / 'config.yaml').read_bytes()
account = 'dashboard:basic:acceptance-owner'
reference = {'id': '472d75ca2a0540ebac6533f67ffb557b', 'revision': 1}
expected = 'Synthetic daily acceptance verification code is D252-TEXT-4109.'
original = json.loads((stage / 'installed-profile-recovery-verification.json').read_text())
signature = original['backup']['signature']
backup = stage / 'application-offserver-extracted/application-tested-profile-backup'
assert hashlib.sha256((backup / 'manifest.json').read_bytes()).hexdigest() == signature
started = time.monotonic()
manifest = module('profile_backup').inspect(configuration, backup, signature, account=account)
assert len(manifest['files']) == original['backup']['profile_files']
recovery = module('profile_backup_recovery').recover(configuration, backup, signature,
    stage / 'application-offserver-profile-recovery', account=account)
assert recovery['status'] == 'recovered'
recovered_profile, recovered_root = Path(recovery['profile']), Path(recovery['root'])
candidate = module('memory_service').MemoryConfiguration(recovered_profile / 'lifeos-memory.json').load()
assert not candidate['ownership_enabled'] and not candidate['sharing_enabled']
scope = module('memory_preferences').MemoryPreferences._owner_scope(candidate)
fact = module('memory_access').NativeMemory(recovered_root, profile=recovered_profile).get(scope, reference)
assert fact['reference'] == reference and fact['content'] == expected
recovered_history = history(recovered_profile / 'state.db')
assert recovered_history == original['history_before']
connector = json.loads((recovered_root / 'LIFEOS/USER/CONFIG/memory-access.json').read_text())
assert connector['command'][-1] == str(recovered_profile / 'lifeos-memory.json')
assert configuration.path.read_bytes() == configuration_before
assert (profile / 'config.yaml').read_bytes() == yaml_before
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
assert services.status()['state'] == 'active'
report = {'status': 'PASS', 'archive': 'ct/101/2026-10-10T03:08:05Z',
    'storage': 'PBS-01', 'restore_node': 'pve-tr1950x',
    'signature': signature, 'recovery': recovery, 'reference': reference,
    'recovered_history': recovered_history, 'elapsed_seconds': round(time.monotonic() - started, 3),
    'source_configuration_preserved': True, 'recovered_connector_verified': True,
    'candidate_ownership_disabled': True, 'candidate_services_started': False,
    'offserver_profile_restore_verified': True, 'full_guest_restore_verified': False,
    'final_release_backup': False, 'live_profile_changed': False,
    'snapshot_boundary': 'The tested profile backup precedes the native core-editor selection change.'}
(stage / 'installed-offserver-profile-recovery-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
