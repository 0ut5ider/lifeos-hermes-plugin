# ABOUTME: Binds the corrective account release to completed exact-package and actual guest recovery checks.
# ABOUTME: Records prior native qualification separately from current execution and pending daily acceptance.
import hashlib
import json
from pathlib import Path
import tarfile

out = Path(__file__).resolve().parent
used = set()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    used.add(name)
    return json.loads((out / name).read_bytes())


def text(name):
    used.add(name)
    return (out / name).read_text()


def passed(name):
    result = load(name)
    assert result['status'] == 'PASS', name
    return result


build = load('stable-build.json')
commit = 'a1abb579558edcf29f7cd04ecfd998995d48db54'
archive_sha = '1c7de7abc4014bfee83bc9bdcd4bfdb6c169526844d44491741d56645f400177'
assert build['head'] == commit and build['version'] == '0.4.3'
assert build['archive_sha256'] == digest(build['archive']) == archive_sha
assert Path(build['archive']).stat().st_size == build['archive_bytes'] == 207693549
integration = load('integration-archive-bound-a1abb579.json')
native = load('native-sealed-a1abb579.json')
for receipt in (integration, native):
    assert receipt['exit_code'] == 0 and receipt['package_commit'] == commit
    assert receipt['archive_sha256'] == archive_sha
assert integration['archive_files_match_before'] and integration['archive_files_match_after']
output = text('integration-archive-bound-a1abb579.stderr')
assert 'Ran 683 tests' in output and output.rstrip().endswith('OK')
assert 'ResourceWarning' not in output and 'skipped' not in output
assert text('integration-archive-bound-a1abb579.done').strip() == '0'
assert '38 files, 716 tests passed, 0 failed (100% complete)' in text('native-sealed-a1abb579.stdout')
assert not text('native-sealed-a1abb579.stderr')
assert text('native-sealed-a1abb579.done').strip() == '0'
with tarfile.open(build['archive']) as archive:
    manifest = archive.extractfile('hermes/hermes-source-manifest.json').read()
    input_names = {'hermes/hermes-source-manifest.json', 'lifeos/lifeos-source-manifest.json',
                   'lifeos_hook_bridge/dependency_locks/catalog.json'}
    candidate_inputs = {name: hashlib.sha256(archive.extractfile(name).read()).hexdigest()
                        for name in input_names}
assert native['source_manifest_sha256'] == hashlib.sha256(manifest).hexdigest()
assert native['source_tree_sha256'] == json.loads(manifest)['tree_sha256']
assert native['archived_source_files_unchanged'] is True and native['bun_version'] == '1.4.3'
assert native['bun_binary_sha256'] == '7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b'
assert 'Ran 39 tests' in text('frozen-focused.stderr') and text('frozen-focused.stderr').rstrip().endswith('OK')
assert 'Ran 4 tests' in text('restore-binding-after.stderr') and text('restore-binding-after.stderr').rstrip().endswith('OK')
unchanged = passed('unchanged-native-inputs.json')
assert unchanged['candidate_archive_sha256'] == archive_sha
assert set(unchanged['inputs']) == input_names
accepted_input_sha256 = {
    'hermes/hermes-source-manifest.json': 'c828676c4915468f8489ae7d572f700115a740e434ac5a4e761771bf74865c69',
    'lifeos/lifeos-source-manifest.json': 'de564ad81fdfa2e6f4a5a1f39bb216a5fc90d63f120fe8ac6e1b5660b25e5991',
    'lifeos_hook_bridge/dependency_locks/catalog.json': '2d4cfce96064f9473747b8b008dd50bf982f6e32d48814b227f99dde57103695'}
for name, row in unchanged['inputs'].items():
    assert row['program_identity_equal'] is True
    assert row['candidate_sha256'] == candidate_inputs[name]
    assert row['accepted_sha256'] == accepted_input_sha256[name]
    assert row['excluded_build_location_fields'] == (['upstream'] if name.startswith('lifeos/') else [])
    assert row['byte_identical'] is (not name.startswith('lifeos/'))
prior_certificate = out.parent / '2026-10-13-release-0.4.2/candidate-87205092/RELEASE-CERTIFICATE.json'
assert digest(prior_certificate) == 'd937719db08eb0218a4f3f037a7132537f4e7ba55b48790467936df8a59e977e'
prior = json.loads(prior_certificate.read_bytes())
assert prior['production_qualified'] and prior['archive_sha256'] == unchanged['accepted_archive_sha256']

applied = passed('verify-applied.json')
restored = passed('verify-restored.json')
final = passed('verify-final-applied.json')
for receipt in (applied, restored, final):
    assert receipt['model_selection_sha256'] == applied['model_selection_sha256']
    assert receipt['synthetic_memory_reference'] == applied['synthetic_memory_reference']
    assert receipt['model_mapping_preserved'] and receipt['native_store_preserved']
    assert not receipt['production_guest_changed'] and not receipt['personal_data_imported_or_reset']
    assert set(receipt['services']) == {'hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'}
    for unit in receipt['services'].values():
        assert set(unit) == {'active', 'native_home_preserved', 'profile_preserved'}
        assert all(value is True for value in unit.values())
for receipt in (applied, final):
    assert receipt['active']['version'] == '0.4.3' and receipt['active']['commit'] == commit
    assert receipt['active']['package_sha256'] == archive_sha and receipt['active']['verification'] == 'verified'
assert restored['active']['version'] == '0.3.1' and restored['active']['verification'] == 'verified'
assert restored['active']['commit'] == '9af633252004a0ac8dd780d5fc12e9644f97bb0c'
assert restored['active']['package_sha256'] == '2aada985dd26dee4ffb4da1d3348c43c76cff2e697d04028cfbba9d6f1b11a24'
interrupted = load('collection-interruption-exit.json')
assert interrupted['exit_status'] == 73 and interrupted['unit_collected'] and interrupted['authenticated_owner_verified']
assert interrupted['candidate_commit'] == commit and interrupted['native_mount_required'] is False
states = passed('daily-layout-operation-states.json')['operations']
assert len(states) == 4
for row in states:
    assert row['program_commit'] == commit and row['archive_sha256'] == archive_sha
    assert row['account_home'] == '/home/lifeos-hermes' and row['native_home'] != row['account_home']
recovered = next(row for row in states if row['operation'] == interrupted['operation'])
assert recovered['state'] == 'rolled_back' and recovered['program_state'] == 'restored'
assert states[0]['state'] == 'rolled_back' and states[0]['program_state'] == 'restored'
operation = 'd5621dc92681425b9ee4553a063b7f0c'
assert states[-1]['operation'] == operation and states[-1]['state'] == states[-1]['program_state'] == 'applied'

whole = passed('bound-whole-guest-recovery.json')
coverage = passed('bound-whole-guest-program-coverage.json')
artifacts = passed('bound-whole-guest-artifact-coverage.json')
captured = passed('source-program-artifact-capture.json')
backup_operations = load('source-backup-operations.json')
assert {'backup-source', 'resume-source'} <= {row['label'] for row in backup_operations if row['exit_code'] == 0}
assert artifacts['private_map_sha256'] == captured['private_map_sha256']
assert artifacts['artifacts'] == captured['artifacts']
assert text('bound-whole-guest-process.done').strip() == '0'
operations = load('bound-whole-guest-operations.json')
required = {'restore', 'disconnect', 'mount', 'unmount', 'boot-isolated', 'verify-history',
            'verify-program-artifacts', 'verify-stable-programs', 'shutdown-restore', 'destroy-disposable'}
assert required <= {row['label'] for row in operations} and all(row['exit_code'] == 0 for row in operations)
for receipt in (whole, coverage, artifacts, captured):
    assert receipt['program_commit'] == commit and receipt['archive_sha256'] == archive_sha
    assert receipt['operation'] == operation
assert whole['archive'] == coverage['backup_archive'] and whole['archive'].startswith('PBS-01:backup/ct/111/')
commands = {row['label']: row['command'] for row in operations}
assert len(commands) == len(operations)
assert commands['restore'] == ['pct', 'restore', '110', whole['archive'], '--storage', 'lifeos-043-tests',
    '--rootfs', 'lifeos-043-tests:120', '--unprivileged', '1', '--onboot', '0', '--hostname', 'lifeos-043-recovery']
assert commands['disconnect'] == ['pct', 'set', '110', '--delete', 'net0', '--onboot', '0',
    '--tags', 'disposable;lifeos-043-recovery']
for label, verb in (('mount', 'mount'), ('unmount', 'unmount'), ('boot-isolated', 'start')):
    assert commands[label] == ['pct', verb, '110']
assert commands['shutdown-restore'] == ['pct', 'shutdown', '110', '--timeout', '90']
assert commands['destroy-disposable'] == ['pct', 'destroy', '110', '--purge', '1']
selected_python = '/home/lifeos-hermes/.hermes/.lifeos-releases/' + operation + '/python-environment/bin/python'
execution = ['pct', 'exec', '110', '--', 'runuser', '-u', 'lifeos-hermes', '--', selected_python, '-B']
operator_path = '/home/lifeos-hermes/releases/qualification-0.4.3/'
assert commands['verify-history'] == execution + [operator_path + 'history_guest_recovery.py',
    'verify', '/home/lifeos-hermes/releases/0.4.3-a1abb579']
assert commands['verify-program-artifacts'] == execution + [operator_path + 'program_artifact_receipt.py', 'verify', operation]
assert commands['verify-stable-programs'] == execution + [operator_path + 'verify_restored_programs.py', operation]
source_commands = {row['label']: row['command'] for row in backup_operations}
assert len(source_commands) == len(backup_operations)
assert source_commands['backup-source'][:6] == ['vzdump', '111', '--storage', 'PBS-01', '--mode', 'stop']
source_execution = ['pct', 'exec', '111', '--', 'runuser', '-u', 'lifeos-hermes', '--', selected_python, '-B']
assert source_commands['capture-program-artifacts'] == source_execution + [operator_path + 'program_artifact_receipt.py', 'capture', operation]
assert source_commands['drain-source'] == source_commands['resume-source'] == source_execution + ['-']
for receipt in (whole, coverage):
    assert receipt['source_guest'] == 111 and receipt['restored_guest'] == 110
    assert receipt['version'] == '0.4.3'
assert whole['network_disconnected'] and whole['application_services_masked']
assert {row['case'] for row in whole['cases']} == {'baseline', 'interrupted', 'later-edit'}
assert len(whole['cases']) == 3 and all(row['status'] == 'PASS' for row in whole['cases'])
for row in whole['cases']:
    assert row['archive_and_live_group_verified'] is True
    assert row['later_edit_refused'] is (row['case'] == 'later-edit')
    assert row['restored_files'] == (51 if row['case'] == 'baseline' else 55)
assert coverage['program_targets'] == 9 and coverage['application_services_masked']
assert whole['runtime_artifact_coverage'] == artifacts
frontend = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')
assert digest(frontend) == prior['hermes_dashboard_sha256']
certificate = {'format': 1, 'status': 'QUALIFIED', 'production_qualified': True,
    'version': '0.4.3', 'program_commit': commit, 'archive_sha256': archive_sha,
    'archive_bytes': build['archive_bytes'], 'hermes_dashboard_sha256': digest(frontend),
    'hermes_base': build['hermes_base'], 'lifeos_base': build['lifeos_base'],
    'hermes_patch_count': build['hermes_patch_count'], 'lifeos_patch_count': build['lifeos_patch_count'],
    'integration_tests': 683, 'native_tests': 716, 'native_test_files': 38, 'focused_account_tests': 39,
    'qualification_scope': 'Corrective account binding, exact package regression, real daily-layout update, rollback, interruption recovery, and disconnected whole-guest restore',
    'native_service_home_and_model_mapping_preserved': True,
    'whole_guest_history_recovery': whole, 'whole_guest_program_coverage': coverage,
    'whole_guest_runtime_coverage': artifacts,
    'prior_native_qualification': {'version': '0.4.2', 'certificate_sha256': digest(prior_certificate),
        'program_inputs': unchanged, 'reexecuted_native_tests': 716,
        'prior_public_installation_retained_as_historical_evidence': True},
    'qualification_receipt_sha256': {name: digest(out / name) for name in sorted(used)},
    'daily_promotion_verified': False, 'automatic_morning_observed': False,
    'public_default_url_replay_for_043': 'Pending public publication',
    'build_manifest_note': 'The immutable package manifest records build-time state. This certificate records completed corrective qualification.'}
target = out / 'RELEASE-CERTIFICATE.json'
assert not target.exists(), 'The release certificate already exists'
target.write_text(json.dumps(certificate, indent=2) + '\n')
print(json.dumps({'status': 'QUALIFIED', 'program_commit': commit,
                  'certificate_sha256': digest(target)}, indent=2))
