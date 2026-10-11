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
                if path.read_bytes()[:16] == b'SQLite format 3\x00':
                    with closing(sqlite3.connect(path)) as connection:
                        assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)], str(path)
                    sqlite[str(path)] = True
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
    for name, expected in value['files'].items():
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
            assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)], name
    configuration = json.loads((home / '.hermes/lifeos-memory.json').read_text())
    assert not configuration['ownership_enabled'] and not configuration['sharing_enabled']
    (evidence / ('coverage-' + case + '-restored.json')).write_text(json.dumps({
        'status': 'PASS', 'case': case, 'exact_files_verified': len(value['files']),
        'symlinks_verified': len(value['symlinks']), 'sqlite_databases_verified': len(value['sqlite_integrity']),
        'external_atlas_covered': True, 'daily_ownership_enabled': False, 'sharing_enabled': False}, indent=2) + '\n')
print(json.dumps({'action': action, 'case': case, 'files': len(value['files']),
    'sqlite_databases': len(value['sqlite_integrity'])}))
