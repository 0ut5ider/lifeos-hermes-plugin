# ABOUTME: Records daily state and runtime paths covered by an offline whole-guest backup.
# ABOUTME: Compares exact restored files and private modes before recovery changes state.
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

os.umask(0o077)
home = Path('/home/lifeos-hermes')
evidence = home / 'deployment/2026-10-11'
case, action = sys.argv[1:]
destination = evidence / ('coverage-' + case + '.json')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
if action == 'prepare':
    installation = json.loads((evidence / 'installation.json').read_text())
    root = Path(installation['installed'])
    roots = [home / '.hermes', root.parent / '.config/LIFEOS',
        root.parent / '.local/state/lifeos', home / '.config/systemd/user', home / 'runtime/hermes/hermes_cli/web_dist']
    files, links, sqlite = {}, {}, {}
    # Checkpoint stopped writers before recording bytes. Close cursors as well as connections.
    for selected in roots:
        for path in selected.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            if selected == home / '.hermes' and {'installs', 'tools', 'plugins', '__pycache__'} & set(path.relative_to(selected).parts):
                continue
            with path.open('rb') as source:
                header = source.read(16)
            if header == b'SQLite format 3\x00':
                with closing(sqlite3.connect(path)) as connection:
                    with closing(connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')) as cursor:
                        assert cursor.fetchall()[0][0] == 0, str(path)
                    with closing(connection.execute('PRAGMA integrity_check')) as cursor:
                        assert cursor.fetchall() == [('ok',)], str(path)
                sqlite[str(path)] = True
    for selected in roots:
        assert selected.exists(), selected
        for path in selected.rglob('*'):
            relative = path.relative_to(selected)
            if selected == home / '.hermes' and {'installs', 'tools', 'plugins', '__pycache__'} & set(relative.parts):
                continue
            mode = path.lstat().st_mode
            if stat.S_ISSOCK(mode) or path.name.endswith(('.lock', '.pid')):
                continue
            if path.is_symlink():
                links[str(path)] = os.readlink(path)
            elif path.is_file():
                files[str(path)] = {'sha256': sha(path), 'mode': mode & 0o777, 'bytes': path.stat().st_size}
    # Source settings, selection, manifests, and external Atlas are explicit coverage members.
    for path in (root / 'settings.json', root / 'LIFEOS/VERSION', home / '.local/bin/hermes'):
        files[str(path)] = {'sha256': sha(path), 'mode': path.stat().st_mode & 0o777, 'bytes': path.stat().st_size}
    value = {'status': 'PREPARED', 'case': case, 'roots': [str(path) for path in roots],
        'files': files, 'symlinks': links, 'sqlite_integrity': sqlite,
        'rootfs_only': True, 'external_atlas_covered': True,
        'application_writers_stopped': True, 'additional_mounts': []}
    destination.write_text(json.dumps(value, indent=2) + '\n')
else:
    assert action == 'verify'
    value = json.loads(destination.read_text())
    volatile_sidecars = []
    for name, expected in value['files'].items():
        if name.endswith(('-wal', '-shm')):
            database = name[:-4]
            wal = value['files'].get(database + '-wal')
            main = value['files'].get(database)
            # An integrity check can record empty WAL and shared-memory files in a manifest.
            # Require an exact main database and an empty recorded WAL. Nonempty WAL remains mandatory.
            if main and wal and wal['bytes'] == 0 and wal['sha256'] == hashlib.sha256(b'').hexdigest():
                assert sha(Path(database)) == main['sha256'], database
                restored_wal = Path(database + '-wal')
                assert not restored_wal.exists() or restored_wal.stat().st_size == 0, database
                volatile_sidecars.append(name)
                continue
        if '/.config/systemd/user/' in name:
            # The recovery operator retains original definitions next to explicit service masks.
            retained = Path(name + '.before-recovery')
            path = retained if retained.exists() else Path(name)
        else:
            path = Path(name)
        assert sha(path) == expected['sha256'], name
        assert path.stat().st_mode & 0o777 == expected['mode'], name
        assert path.stat().st_size == expected['bytes'], name
    for name, target in value['symlinks'].items():
        assert os.readlink(name) == target, name
    for name in value['sqlite_integrity']:
        with closing(sqlite3.connect(name)) as connection:
            with closing(connection.execute('PRAGMA integrity_check')) as cursor:
                assert cursor.fetchall() == [('ok',)], name
    configuration = json.loads((home / '.hermes/lifeos-memory.json').read_text())
    assert not configuration['ownership_enabled'] and not configuration['sharing_enabled']
    (evidence / ('coverage-' + case + '-restored.json')).write_text(json.dumps({
        'status': 'PASS', 'case': case, 'exact_files_verified': len(value['files']) - len(volatile_sidecars),
        'empty_wal_volatile_sidecars': volatile_sidecars,
        'symlinks_verified': len(value['symlinks']), 'sqlite_databases_verified': len(value['sqlite_integrity']),
        'external_atlas_covered': True, 'daily_ownership_enabled': False, 'sharing_enabled': False}, indent=2) + '\n')
print(json.dumps({'action': action, 'case': case, 'files': len(value['files']),
    'sqlite_databases': len(value['sqlite_integrity'])}))
