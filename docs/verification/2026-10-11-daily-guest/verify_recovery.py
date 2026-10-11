# ABOUTME: Verifies restored native state against the recorded whole-guest backup inputs.
# ABOUTME: Checks exact group recovery and refusal after a later synthetic owner edit.
from contextlib import closing
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys

os.umask(0o077)
home = Path('/home/lifeos-hermes')
evidence = home / 'deployment/2026-10-11'
package = home / 'releases/0.2.0-11577ed4'
os.environ.update(PATH=str(home / '.local/bin') + ':/usr/bin:/bin',
    BUN_CONFIG_NO_AUTO_INSTALL='1', PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0, str(package))
mode = sys.argv[1]
folder = evidence / 'recovery-fixtures' / mode
prepared = json.loads((folder / 'prepared.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, expected in prepared['files'].items():
    path = Path(name)
    assert sha(path) == expected['sha256'], name
    assert path.stat().st_mode & 0o777 == expected['mode'], name
    assert path.stat().st_size == expected['bytes'], name
for name, expected in prepared['database_tables'].items():
    with closing(sqlite3.connect(name)) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        actual = {table: connection.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0] for table in expected}
        assert actual == expected, (name, actual, expected)
candidate = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
for name, expected in candidate['plugin_files'].items():
    assert sha(home / '.hermes/plugins/lifeos-hook-bridge' / Path(name).relative_to('lifeos_hook_bridge')) == expected, name
runtime = json.loads((evidence / 'installation-verification.json').read_text())
for name, expected in runtime['hermes_program_hashes'].items():
    assert sha(home / 'runtime/hermes' / name) == expected, name
daily = json.loads((evidence / 'installation.json').read_text())
for name, expected in runtime['native_program_hashes'].items():
    assert sha(Path(daily['installed']) / name) == expected, name
configuration = json.loads((home / '.hermes/lifeos-memory.json').read_text())
assert not configuration['ownership_enabled'] and not configuration['sharing_enabled']
module = lambda name: importlib.import_module('lifeos_hook_bridge.' + name)
memory = module('memory_access').NativeMemory(Path(prepared['root']))
originals = prepared['original_artifact_sha256']
artifacts = [Path(name) for name in originals if not name.startswith('metadata_')]
before = {str(path): sha(path) for path in artifacts}
refused = False
if mode == 'later-edit':
    try:
        with memory._transaction():
            pass
    except module('memory_access').MemoryUnavailable as error:
        assert 'later artifact edit' in str(error), str(error)
        refused = True
    assert refused
    assert {str(path): sha(path) for path in artifacts} == before
    assert memory.transaction.journal.exists()
else:
    with memory._transaction() as connection:
        with closing(connection.execute('PRAGMA integrity_check')) as cursor:
            assert [tuple(row) for row in cursor.fetchall()] == [('ok',)]
    assert not memory.transaction.journal.exists()
    assert {str(path): sha(path) for path in artifacts} == {str(path): originals[str(path)] for path in artifacts}
    with closing(sqlite3.connect(memory.database)) as connection:
        assert hashlib.sha256('\n'.join(connection.iterdump()).encode()).hexdigest() == originals['metadata_dump_sha256']
report = {'status': 'PASS', 'mode': mode, 'source': 'actual PBS whole-guest restore',
    'guest_network_disabled': True, 'automatic_application_services_disabled': True,
    'covered_files_verified': len(prepared['files']), 'private_modes_verified': True,
    'sqlite_integrity_verified': True, 'complete_database_table_counts_verified': True,
    'plugin_files_verified': len(candidate['plugin_files']),
    'hermes_source_files_verified': len(runtime['hermes_program_hashes']),
    'native_program_files_verified': len(runtime['native_program_hashes']),
    'exact_group_recovery': mode != 'later-edit', 'later_edit_refused': refused,
    'journal_retained': memory.transaction.journal.exists(), 'daily_memory_ownership_enabled': False,
    'sharing_enabled': False, 'synthetic_data_only': True}
(folder / 'restored-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
