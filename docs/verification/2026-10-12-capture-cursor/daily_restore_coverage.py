# ABOUTME: Records private daily data and selected program hashes while owner writers are stopped.
# ABOUTME: Verifies restored bytes, modes, symlinks, and masked service originals without exporting content.
import argparse
import hashlib
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('prepare', 'verify'))
args = parser.parse_args()
os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
release = json.loads((profile / 'integration-release.json').read_text())
assert release['version'] == '0.3.1'
root = Path(json.loads((profile / 'lifeos-memory.json').read_text())['root'])
output = home / 'deployment' / ('release-' + release['version'] + '-' + release['commit'][:8])
record = output / 'daily-restore-coverage-private.json'
units = home / '.config/systemd/user'
masked = {'hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'}

def describe(path):
    info = path.lstat()
    value = {'mode': info.st_mode & 0o777, 'uid': info.st_uid, 'gid': info.st_gid}
    if path.is_symlink():
        value.update(kind='symlink', target=os.readlink(path))
    elif path.is_file():
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        value.update(kind='file', sha256=digest.hexdigest())
    elif path.is_dir():
        value['kind'] = 'directory'
    else:
        raise RuntimeError('The selected daily tree contains an unsupported artifact')
    return value

if args.action == 'prepare':
    assert not record.exists()
    directories = [profile, units, home / '.local/bin', home / '.local/libexec',
        home / 'runtime/releases' / (release['version'] + '-' + release['commit'][:8]),
        (root / 'LIFEOS/USER').resolve(), root.parent / '.local/state/lifeos/atlas']
    paths = set()
    for directory in directories:
        if directory.exists():
            paths.add(directory)
            paths.update(directory.rglob('*'))
    artifacts = {str(path): describe(path) for path in sorted(paths)}
    record.write_text(json.dumps({'version': release['version'], 'commit': release['commit'],
        'artifacts': artifacts}, indent=2) + '\n')
    record.chmod(0o600)
    report = {'status': 'PREPARED', 'artifacts': len(artifacts), 'contents_exported': False}
else:
    captured = json.loads(record.read_text())
    assert captured['version'] == release['version'] and captured['commit'] == release['commit']
    for name, expected in captured['artifacts'].items():
        path = Path(name)
        if path.parent == units and path.name in masked:
            assert path.is_symlink() and os.readlink(path) == '/dev/null'
            path = units / (path.name + '.before-restore')
        assert describe(path) == expected, 'The daily restore changes a selected artifact'
    report = {'status': 'PASS', 'version': release['version'], 'commit': release['commit'],
        'artifacts': len(captured['artifacts']), 'bytes_modes_and_links_verified': True,
        'selected_profile_and_credentials_verified': True, 'personal_store_and_atlas_verified': True,
        'selected_programs_and_service_originals_verified': True, 'contents_exported': False}
    (output / 'daily-restore-coverage-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
