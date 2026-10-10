# ABOUTME: Verifies the isolated candidate package and its pinned source manifests on .252.
# ABOUTME: Compares runtime lock inputs without loading transport credentials or memory records.
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
sys.path.insert(0, str(package))
from lifeos_hook_bridge.install_source import validate_prepared_lifeos, validate_supported_hermes

manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for category in ('prepared_manifest_files', 'plugin_files', 'daily_configuration_files'):
    for name, digest in manifest[category].items():
        if sha(package / name) != digest:
            raise RuntimeError('The staged candidate changes ' + name)
hermes = validate_supported_hermes(package / 'hermes')
lifeos = validate_prepared_lifeos(package / 'lifeos')
current = Path('/home/lifeos-hermes/workspace/hermes-agent')
locks = {}
for name in ('pyproject.toml', 'uv.lock', 'pm/lock.json'):
    candidate = package / 'hermes' / name
    previous = current / name
    locks[name] = {'candidate': sha(candidate), 'installed': sha(previous)}
    if locks[name]['candidate'] != locks[name]['installed']:
        raise RuntimeError('The installed Python dependency input differs: ' + name)
report = {'head': manifest['head'], 'plugin_files': len(manifest['plugin_files']),
    'hermes_base': hermes['base_commit'], 'lifeos_base': lifeos['upstream_commit'],
    'candidate_manifests_valid': True, 'runtime_lock_inputs': locks,
    'live_services_changed': False, 'transport_credentials_loaded': False}
(stage / 'package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
