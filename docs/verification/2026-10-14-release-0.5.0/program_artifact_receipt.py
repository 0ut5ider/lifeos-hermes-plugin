# ABOUTME: Captures and verifies all selected release runtime artifacts for whole-guest restoration.
# ABOUTME: Keeps file maps private and exports only counts, digests, and release identity.
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

os.umask(0o077)
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('capture', 'verify'))
parser.add_argument('operation')
args = parser.parse_args()
profile = Path.home() / '.hermes'
job = profile / '.lifeos-releases' / args.operation
stage = Path.home() / 'releases/qualification-0.5.0'
request = json.loads((job / 'request.json').read_bytes())
assert request['commit'] == '04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert request['package_sha256'] == 'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
assert json.loads((job / 'status.json').read_bytes())['state'] == 'applied'
roots = {name: job / name for name in ('worker', 'hermes', 'python-environment', 'pm-runtime',
    'tools', 'bin', 'compiled-dashboard', 'package', 'dependency-profile')}
python = Path(request['runtime']['python']).resolve(strict=True)
assert python.is_relative_to(job / 'dependency-profile/tools')
manifest = stage / 'program-artifact-map.private.json'


def entries():
    result = {}
    for label, root in roots.items():
        assert root.is_dir() and not root.is_symlink()
        pending = [root]
        while pending:
            path = pending.pop()
            before = path.lstat()
            key = label + '/' + path.relative_to(root).as_posix()
            row = {'mode': stat.S_IMODE(before.st_mode), 'uid': before.st_uid}
            if stat.S_ISLNK(before.st_mode):
                row.update(kind='link', target=os.readlink(path))
            elif stat.S_ISDIR(before.st_mode):
                row['kind'] = 'directory'
                pending.extend(sorted(path.iterdir(), reverse=True))
            elif stat.S_ISREG(before.st_mode):
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                after = path.lstat()
                assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), key
                row.update(kind='file', sha256=digest.hexdigest(), bytes=before.st_size)
            else:
                raise RuntimeError('A runtime artifact is not a regular file, directory, or link')
            result[key] = row
    return result


current = entries()
if args.action == 'capture':
    assert not manifest.exists()
    manifest.write_text(json.dumps({'operation': args.operation,
        'program_commit': request['commit'], 'entries': current}, sort_keys=True) + '\n')
    manifest.chmod(0o600)
else:
    saved = json.loads(manifest.read_bytes())
    assert saved['operation'] == args.operation and saved['program_commit'] == request['commit']
    assert current == saved['entries'], 'Restored runtime artifacts differ from the captured source'
report = {'status': 'PASS', 'action': args.action, 'operation': args.operation,
    'program_commit': request['commit'], 'archive_sha256': request['package_sha256'],
    'artifacts': len(current), 'regular_files': sum(row['kind'] == 'file' for row in current.values()),
    'bytes': sum(row.get('bytes', 0) for row in current.values()),
    'private_map_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
    'runtime_roots': sorted(roots), 'private_map_exported': False}
(stage / ('program-artifact-' + args.action + '.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
