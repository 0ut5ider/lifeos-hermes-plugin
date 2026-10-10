# ABOUTME: Produces the Content source and static export patch from the complete native build.
# ABOUTME: Prepares and validates the complete pinned source without replacing historical fixtures.
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

repository = Path(__file__).resolve().parents[3]
cache = Path('/home/outsider/.cache/lifeos-daily-text-20261007')
base = cache / 'algorithm-prompt-transport-second/lifeos/LifeOS/install'
built = cache / 'content-response-first/lifeos/LifeOS/install'
relative = Path('LIFEOS/PULSE/Observability')
def difference(left, right, target):
    process = subprocess.run(['git', 'diff', '--no-index', '--binary', '--no-renames', str(left), str(right)], capture_output=True)
    assert process.returncode in (0, 1), process.stderr
    value = process.stdout.replace(('a' + str(left)).encode(), ('a/LifeOS/install/' + target).encode())
    value = value.replace(('b' + str(right)).encode(), ('b/LifeOS/install/' + target).encode())
    return value
patch = difference(base / relative / 'src/app/content/page.tsx', built / relative / 'src/app/content/page.tsx', str(relative / 'src/app/content/page.tsx'))
patch += difference(base / relative / 'out', built / relative / 'out', str(relative / 'out'))
for folder in ('patches', 'lifeos_hook_bridge/patches'):
    (repository / folder / 'lifeos-content-response-consumption.patch').write_bytes(patch)
sys.path.insert(0, str(repository))
from lifeos_hook_bridge.install_source import prepare_lifeos, validate_prepared_lifeos, SUPPORTED_LIFEOS_COMMIT, LIFEOS_PATCHES
prepared = cache / 'content-response-fourth/lifeos'
assert not prepared.exists()
manifest = prepare_lifeos(str(cache / 'channel-sources/lifeos'), prepared, SUPPORTED_LIFEOS_COMMIT,
    repository / 'lifeos_hook_bridge/patches', LIFEOS_PATCHES)
assert validate_prepared_lifeos(prepared) == manifest
payload = cache / 'content-response-second-payload'
assert not payload.exists()
payload.mkdir(mode=0o700)
inputs = {'content-page.tsx': built / relative / 'src/app/content/page.tsx',
    'install_source.py': repository / 'lifeos_hook_bridge/install_source.py',
    'lifeos-content-response-consumption.patch': repository / 'lifeos_hook_bridge/patches/lifeos-content-response-consumption.patch',
    'lifeos-source-manifest.json': prepared / 'lifeos-source-manifest.json'}
for name, source in inputs.items(): (payload / name).write_bytes(source.read_bytes())
with tarfile.open(payload / 'exports.tgz', 'w:gz') as archive: archive.add(built / relative / 'out', arcname='out')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def digest(directory):
    result = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            result.update(path.relative_to(directory).as_posix().encode() + b'\0' + sha(path).encode() + b'\n')
    return result.hexdigest()
before = json.loads((cache / 'content-response-payload/selection.json').read_text())
assert digest(prepared / 'LifeOS/install' / relative / 'out') == digest(built / relative / 'out')
spec = {'before_export_sha256': before['after_export_sha256'], 'after_export_sha256': digest(built / relative / 'out'),
    'source_before_sha256': before['files']['content-page.tsx'],
    'patch_before_sha256': before['files']['lifeos-content-response-consumption.patch'],
    'files': {name: sha(payload / name) for name in inputs}, 'export_archive_sha256': sha(payload / 'exports.tgz')}
(payload / 'selection.json').write_text(json.dumps(spec, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'patch_count': len(manifest['patches']), 'spec': spec}, indent=2))
