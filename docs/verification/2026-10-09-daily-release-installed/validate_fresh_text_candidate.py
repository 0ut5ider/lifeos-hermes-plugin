# ABOUTME: Verifies the fresh versioned candidate archive and pinned source manifests on the development guest.
# ABOUTME: Compares installed dependency inputs without reading memory records or transport credentials.
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-0.2.0-ea4ad3c5')
package = stage / 'package'
sys.path.insert(0, str(package))
from lifeos_hook_bridge.install_source import validate_prepared_lifeos, validate_supported_hermes

manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for category in ('prepared_manifest_files', 'plugin_files', 'daily_configuration_files'):
    for name, digest in manifest[category].items():
        assert sha(package / name) == digest, name
version = (package / 'VERSION').read_text().strip()
assert version == manifest['version'] == '0.2.0'
assert json.loads((package / 'lifeos_hook_bridge/dashboard/manifest.json').read_text())['version'] == version
assert re.search(r'^version: (.+)$', (package / 'lifeos_hook_bridge/plugin.yaml').read_text(), re.M).group(1) == version
hermes = validate_supported_hermes(package / 'hermes')
lifeos = validate_prepared_lifeos(package / 'lifeos')
installed = Path('/home/lifeos-hermes/workspace/hermes-agent')
locks = {}
for name in ('pyproject.toml', 'uv.lock', 'pm/lock.json'):
    locks[name] = {'candidate': sha(package / 'hermes' / name), 'installed': sha(installed / name)}
    assert locks[name]['candidate'] == locks[name]['installed'], name
report = {'status': 'PASS', 'version': version, 'head': manifest['head'],
    'plugin_file_count': len(manifest['plugin_files']),
    'hermes_base': hermes['base_commit'], 'lifeos_base': lifeos['upstream_commit'],
    'candidate_manifests_valid': True, 'runtime_lock_inputs': locks,
    'bun_version': subprocess.check_output(['/home/lifeos-hermes/.local/bin/bun', '--version'], text=True).strip(),
    'live_services_changed': False, 'transport_credentials_loaded': False,
    'memory_records_read': False, 'combined_release_verified': False}
(stage / 'fresh-text-candidate-installed.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
