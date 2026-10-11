# ABOUTME: Creates synthetic native Atlas state for whole-guest recovery checks.
# ABOUTME: Retains exact original artifacts and actual interrupted publication journals outside daily data.
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

os.umask(0o077)
account_home = Path('/home/lifeos-hermes')
evidence = account_home / 'deployment/2026-10-11'
package = account_home / 'releases/0.2.0-11577ed4'
mode = sys.argv[1]
assert mode in ('baseline', 'interrupted', 'later-edit')
os.environ.update(PATH=str(account_home / '.local/bin') + ':/usr/bin:/bin',
    PYTHONPATH=str(package), PYTHONDONTWRITEBYTECODE='1', BUN_CONFIG_NO_AUTO_INSTALL='1')
sys.path.insert(0, str(package))
module = lambda name: importlib.import_module('lifeos_hook_bridge.' + name)
source = Path(json.loads((evidence / 'installation.json').read_text())['installed'])
folder = evidence / 'recovery-fixtures' / mode
folder.mkdir(parents=True, mode=0o700)
home = folder / 'home'
root = home / '.claude'
data = home / '.config/LIFEOS/USER'
shutil.copytree(source, root, symlinks=True)
shutil.copytree(source / 'LIFEOS/USER', data, symlinks=True)
for path, target in ((root / 'LIFEOS/USER', data), (root / 'LIFEOS/MEMORY', data / 'MEMORY')):
    assert path.is_symlink()
    path.unlink()
    path.symlink_to(target, target_is_directory=True)
profile = home / '.hermes'
profile.mkdir(mode=0o700)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
configuration.save({'version': 1, 'root': str(root), 'principal': 'synthetic-owner',
    'ownership_enabled': False, 'sharing_enabled': False,
    'accounts': {'terminal:' + str(os.getuid()): 'synthetic-owner'},
    'destinations': {'terminal:' + str(profile): {'visibility': 'private', 'participants': ['synthetic-owner'],
        'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
        'projects': ['*'], 'model_routes': ['local']}}, 'clients': {}})
context = module('memory_policy').SessionContext('terminal', str(os.getuid()), str(profile),
    'private', ('synthetic-owner',), 'local', 'synthetic-guest-' + mode)
connector = root / 'LIFEOS/USER/CONFIG/memory-access.json'
connector.write_text(json.dumps({'version': 1, 'command': [sys.executable,
    str(package / 'lifeos_hook_bridge/memory_rpc.py'), '--configuration', str(configuration.path)]}))
connector.chmod(0o600)
(data / 'GEAR.md').write_text('## Computing\n| **Laptop** | Synthetic Guest Machine | daily |\n')
(data / 'PROJECTS.md').write_text('| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'
    '| Synthetic Guest Project | /synthetic/guest | guest.example.invalid | local |\n')
service = module('memory_service').MemoryService(configuration)
receipt = service.call_context(context, 'lifeos_memory_remember', {'category': 'project',
    'content': 'Synthetic guest recovery marker ' + mode, 'title': 'Synthetic guest recovery',
    'project': 'guest-recovery', 'request_id': 'guest-recovery-' + mode})
assert receipt['status'] == 'committed', receipt
result = service.native(context, 'atlas_sync', {'collectors': ['gear', 'projects'], 'scope': 'full'})
assert result['ok'], result
prepared = service.native(context, 'atlas_insight_prepare', {})
assert prepared['ok'] and prepared['plan']['metrics'] is not None, prepared
cache_value = {'hash': prepared['plan']['hash'], 'narrative': 'Synthetic guest recovery narrative.',
    'generated_at': datetime.now(timezone.utc).isoformat()}
assert service.native(context, 'atlas_insight_publish', {'signature': prepared['signature'], 'value': cache_value})['ok']
graph = home / '.local/state/lifeos/atlas/atlas.db'
snapshot = graph.with_name('snapshot.json')
cache = data / 'MEMORY/STATE/atlas-insights.json'
events = graph.with_name('events.jsonl')
events.write_text('{"source":"gear","synthetic":"guest-recovery"}\n')
events.chmod(0o600)
memory = module('memory_access').NativeMemory(root)
artifacts = (graph, snapshot, cache)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
originals = {str(path): sha(path) for path in artifacts}
originals['metadata_database'] = sha(memory.database)
with closing(sqlite3.connect(memory.database)) as connection:
    originals['metadata_dump_sha256'] = hashlib.sha256('\n'.join(connection.iterdump()).encode()).hexdigest()
if mode != 'baseline':
    (data / 'GEAR.md').write_text('## Computing\n| **Laptop** | Synthetic Guest Machine | daily |\n'
        '| **Server** | Synthetic Later Machine | local |\n')
    process = subprocess.run([sys.executable, '-B', str(package / 'tests/memory_atlas_sync_process.py'),
        str(configuration.path), json.dumps(asdict(context)), 'interrupt'],
        env=dict(os.environ), capture_output=True, text=True, timeout=60)
    assert (process.returncode, process.stdout, process.stderr) == (73, '', ''), process
    assert memory.transaction.journal.exists()
if mode == 'later-edit':
    value = json.loads(snapshot.read_text())
    value['generated_at'] = 'Synthetic later owner edit after interrupted publication'
    snapshot.write_text(json.dumps(value))
files = {}
for path in home.rglob('*'):
    if not path.is_file() or path.is_symlink() or 'node_modules' in path.parts:
        continue
    files[str(path)] = {'sha256': sha(path), 'mode': path.stat().st_mode & 0o777, 'bytes': path.stat().st_size}
databases = {}
for database in (graph, memory.database):
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        databases[str(database)] = {table: connection.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0] for table in tables}
report = {'status': 'PREPARED', 'mode': mode, 'home': str(home), 'root': str(root),
    'profile': str(profile), 'files': files, 'original_artifact_sha256': originals,
    'synthetic_fact_receipt': receipt, 'database_tables': databases,
    'publication_journal_present': memory.transaction.journal.exists(),
    'ownership_enabled': False, 'sharing_enabled': False, 'automatic_services': False,
    'daily_store_changed': False}
(folder / 'prepared.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'PREPARED', 'mode': mode, 'covered_files': len(files),
    'database_tables': databases, 'publication_journal_present': report['publication_journal_present']}, indent=2))
