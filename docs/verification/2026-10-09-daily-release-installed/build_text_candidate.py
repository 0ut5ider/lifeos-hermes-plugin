# ABOUTME: Builds a fresh committed daily text candidate with complete pinned native source manifests.
# ABOUTME: Records package bytes and versions without selecting a live installation or loading credentials.
import hashlib
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

repository = Path(__file__).resolve().parents[3]
evidence = Path(__file__).resolve().parent
cache = Path('/home/outsider/.cache/lifeos-daily-text-20261007')
parser = argparse.ArgumentParser()
parser.add_argument('--tag', choices=('candidate', 'output-fixed'), default='candidate')
tag = parser.parse_args().tag
label = 'fresh-text-candidate' if tag == 'candidate' else 'fresh-text-candidate-output-fixed'
package = cache / ('daily-text-0.2.0-' + tag)
archive = cache / ('daily-text-0.2.0-' + tag + '.tgz')
os.umask(0o077)
assert not package.exists() and not archive.exists()
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repository).strip()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
package.mkdir(mode=0o700)
selected = ['lifeos_hook_bridge', 'scripts', 'tests', 'docs/deployment/daily-text',
    'VERSION', 'CHANGELOG.md', 'README.md']
committed = subprocess.check_output(['git', 'archive', head, '--', *selected], cwd=repository)
with tarfile.open(fileobj=io.BytesIO(committed)) as source:
    source.extractall(package, filter='data')
sys.path.insert(0, str(package))
from lifeos_hook_bridge import install_source

started = time.monotonic()
lifeos = install_source.prepare_lifeos(str(cache / 'channel-sources/lifeos'), package / 'lifeos',
    install_source.SUPPORTED_LIFEOS_COMMIT, package / 'lifeos_hook_bridge/patches', install_source.LIFEOS_PATCHES)
hermes = install_source.prepare_supported_hermes(cache / 'daily-hermes-clean-base', package / 'hermes')
assert install_source.validate_prepared_lifeos(package / 'lifeos') == lifeos
assert install_source.validate_supported_hermes(package / 'hermes') == hermes
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
plugin_files = {path.relative_to(package).as_posix(): sha(path)
    for path in sorted((package / 'lifeos_hook_bridge').rglob('*')) if path.is_file() and '__pycache__' not in path.parts}
daily_files = {path.relative_to(package).as_posix(): sha(path)
    for path in sorted((package / 'docs/deployment/daily-text').iterdir()) if path.is_file()}
version = (package / 'VERSION').read_text().strip()
assert version == '0.2.0'
assert json.loads((package / 'lifeos_hook_bridge/dashboard/manifest.json').read_text())['version'] == version
assert ('version: ' + version + '\n') in (package / 'lifeos_hook_bridge/plugin.yaml').read_text()
manifest = {'version': version, 'head': head, 'status': 'release_candidate',
    'plugin_files': plugin_files, 'daily_configuration_files': daily_files,
    'prepared_manifest_files': {name: sha(package / name) for name in
        ('lifeos/lifeos-source-manifest.json', 'hermes/hermes-source-manifest.json')},
    'native_manifests_verified': True, 'live_selection_changed': False,
    'channel_acceptance_verified': False, 'combined_release_verified': False}
(package / 'DAILY-CANDIDATE.json').write_text(json.dumps(manifest, indent=2) + '\n')
with tarfile.open(archive, 'w:gz', compresslevel=6) as output:
    for path in sorted(package.iterdir()):
        output.add(path, arcname=path.name, filter=lambda info: None if '__pycache__' in Path(info.name).parts else info)
digest = hashlib.sha256()
with archive.open('rb') as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
report = {'status': 'PASS', 'version': version, 'head': head,
    'package': str(package), 'archive': str(archive), 'archive_bytes': archive.stat().st_size,
    'archive_sha256': digest.hexdigest(), 'plugin_file_count': len(plugin_files),
    'hermes_base': hermes['base_commit'], 'lifeos_base': lifeos['upstream_commit'],
    'hermes_patch_count': len(hermes['patches']), 'lifeos_patch_count': len(lifeos['patches']),
    'elapsed_seconds': round(time.monotonic() - started, 3),
    'native_manifests_verified': True, 'live_selection_changed': False,
    'combined_release_verified': False}
(evidence / (label + '-manifest.json')).write_text(json.dumps(manifest, indent=2) + '\n')
(evidence / (label + '-build.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
