# ABOUTME: Exercises the retained development program selection and restores the tested release.
# ABOUTME: Checks data hashes while writers are drained and preserves every program directory.
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('package', type=Path)
args = parser.parse_args()
os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
package = args.package.resolve()
sys.path[:0] = [str(package), str(package / 'hermes')]
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
from lifeos_hook_bridge.installation_lock import installation_lock
from lifeos_hook_bridge.memory_transaction import publish
from lifeos_hook_bridge.profile_services import ProfileServices
from lifeos_hook_bridge.release_version import status
manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
evidence = home / 'deployment' / ('release-' + manifest['version'] + '-' + manifest['head'][:8])
selection = json.loads((evidence / 'selection.json').read_text())
assert selection['native_program_changes'] == 0
assert os.getuid() == 1008, 'The rollback exercise selects only the development guest'
root = Path(json.loads((profile / 'lifeos-memory.json').read_text())['root'])
bridge = profile / 'plugins/lifeos-hook-bridge'
rows = json.loads((evidence / 'retained-files.json').read_text())
current = []
for row in rows:
    path = Path(row['path'])
    current.append((path, path.read_bytes() if path.is_file() else None,
        path.stat().st_mode & 0o777 if path.is_file() else 0o600))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def data_hashes():
    files = [profile / '.env', profile / 'lifeos-memory.json']
    for directory in (root / 'LIFEOS/USER', root.parent / '.local/state/lifeos/atlas', profile / 'memories'):
        if directory.is_dir():
            files.extend(p for p in directory.resolve().rglob('*') if p.is_file() and not p.is_symlink())
    return {str(p): sha(p) for p in files if p.is_file()}
def restore_files(values):
    for path, data, mode in values:
        if data is None:
            path.unlink(missing_ok=True)
        else:
            publish(path, data, mode=mode)
with installation_lock(profile) as lease:
    services = ProfileServices(profile, root, installation_lease=lease)
    services.drain(signature=services.preview()['signature'])
    services.verify_stopped()
    before = data_hashes()
    retained_current = evidence / 'rollback-current-plugin'
    assert not retained_current.exists()
    bridge.rename(retained_current)
    try:
        shutil.copytree(evidence / 'plugin-before', bridge, symlinks=True)
        prior = [(Path(row['path']), None if row['retained'] is None else
            (evidence / row['retained']).read_bytes(), row['mode']) for row in reversed(rows)]
        restore_files(prior)
        assert data_hashes() == before
        old = status(profile, bridge)['active']
        assert old['verification'] == 'verified' and old['version'] == '0.3.0-dev.2'
        services.resume()
        launcher = home / 'workspace/hermes-agent/.hermes/bin/hermes'
        result = subprocess.run([str(launcher), 'lifeos-version'], capture_output=True,
            text=True, timeout=60, cwd=profile)
        assert result.returncode == 0 and not result.stderr
        assert json.loads(result.stdout)['active']['commit'] == old['commit']
        services.drain(signature=services.preview()['signature'])
        services.verify_stopped()
        after_prior = data_hashes()
    finally:
        if services.status()['state'] == 'active':
            services.drain(signature=services.preview()['signature'])
        services.verify_stopped()
        if bridge.exists():
            bridge.rename(evidence / 'rollback-prior-plugin')
        retained_current.rename(bridge)
        restore_files(current)
        assert data_hashes() == (after_prior if 'after_prior' in locals() else before)
        selected = status(profile, bridge)['active']
        assert selected['verification'] == 'verified' and selected['commit'] == manifest['head']
        services.resume()
report = {'status': 'PASS', 'prior': old, 'selected': selected,
    'existing_data_preserved_each_selection': True, 'data_files': len(before),
    'prior_runtime_command_verified': True, 'programs_retained': True}
(evidence / 'rollback-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
