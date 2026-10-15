# ABOUTME: Checks the exact selected program targets in a disconnected restored guest.
# ABOUTME: Verifies private configuration bytes without exporting their values.
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
from ruamel.yaml import YAML

if sys.flags.optimize:
    raise RuntimeError('Restore verification requires assertions')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
identifier = sys.argv[1]
assert len(identifier) == 32 and all(c in '0123456789abcdef' for c in identifier)
source = Path('/home/lifeos-hermes/.hermes/.lifeos-releases') / identifier / 'package'
sys.path[:0] = [str(source), str(source / 'hermes')]
from optional.lifeos_release_manager.release_operation import validate_plan
from optional.lifeos_release_manager.release_programs import ProgramTransaction
from optional.lifeos_release_manager import release_worker as worker

profile = Path('/home/lifeos-hermes/.hermes')
job = profile / '.lifeos-releases' / sys.argv[1]
request = json.loads((job / 'request.json').read_bytes())
assert request['version'] == '0.6.0'
assert request['commit'] == 'c86b5887b899ca779afbb217c33843e1ee12c381'
assert request['package_sha256'] == '9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7'
assert json.loads((job / 'status.json').read_bytes())['state'] == 'applied'
plan = validate_plan(job, request)
assert plan['fresh'] is False and plan['native_mount_required'] is False
transaction = ProgramTransaction(job / 'program-snapshot',
    expected_entries_sha256=plan['program_entries_sha256'])
current = worker.recovery_bridge(job, profile)
module = current.memory_module('mount_transaction')
baseline = current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)
mount = module.MountTransaction(Path(request['installed']), profile, baseline)
worker.check_restore(job, request, plan, mount)
mount_before = json.loads((Path('/home/lifeos-hermes/releases/qualification-0.6.0/daily-owner-mount-before.json')).read_bytes())
assert mount_before['status'] == 'PASS' and mount_before['state'] == 'committed'
assert hashlib.sha256(mount.journal.read_bytes()).hexdigest() == mount_before['current_owner_mount_sha256']
mount.check_completed()
programs = transaction._load()
units = Path('/home/lifeos-hermes/.config/systemd/user')
for name in ('hermes-dashboard.service', 'hermes-gateway.service', 'com.lifeos.pulse.service'):
    assert (units / name).is_symlink() and os.readlink(units / name) == '/dev/null'
    assert (units / (name + '.before-restore')).is_file()
preserved = json.loads((Path('/home/lifeos-hermes/releases/qualification-0.6.0/private-preservation-baseline.json')).read_bytes())
assert set(preserved) == {'.env', 'lifeos-memory.json'}
configuration_before = json.loads(Path('/home/lifeos-hermes/releases/qualification-0.6.0/daily-preapply-baseline.json').read_bytes())
configuration = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
assert hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest() == configuration_before['configuration_semantic_sha256']
assert all(hashlib.sha256((profile / name).read_bytes()).hexdigest() == digest for name, digest in preserved.items())
pulse_before = json.loads(Path('/home/lifeos-hermes/releases/qualification-0.6.0/daily-pulse-before.json').read_bytes())
root = Path(json.loads((profile / 'lifeos-memory.json').read_bytes())['root'])
pulse_file = root / 'LIFEOS/USER/CONFIG/PULSE.user.toml'
assert pulse_before['status'] == 'PASS' and hashlib.sha256(pulse_file.read_bytes()).hexdigest() == pulse_before['pulse_user_configuration_sha256']
pulse = tomllib.loads(pulse_file.read_text())
morning = [row for row in pulse['job'] if row['name'] == 'life-morning-brief']
assert len(morning) == 1 and morning[0]['schedule'] == '0 7 * * *' and morning[0]['enabled'] is True
assert pulse['modules']['hermes'] is True
receipt = json.loads((profile / 'integration-release.json').read_bytes())
assert all(receipt[key] == request[key] for key in ('version', 'commit', 'package_sha256'))
print(json.dumps({'status': 'PASS', 'operation': job.name, 'version': request['version'],
    'program_commit': request['commit'], 'archive_sha256': request['package_sha256'],
    'program_targets': len(programs['entries']), 'application_services_masked': True,
    'native_mount_required': False, 'native_mount_targets': len(mount._manifest()['entries']),
    'current_owner_mount_journal_preserved': True,
    'owner_memory_configuration_verified': True, 'credential_file_bytes_preserved': True,
    'private_configuration_exported': False, 'complete_configuration_semantics_preserved': True, 'pulse_user_configuration_preserved': True,
    'normal_morning_schedule': '0 7 * * *', 'pulse_editor_enabled': True}, indent=2))
