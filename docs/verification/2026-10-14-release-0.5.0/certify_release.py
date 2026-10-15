# ABOUTME: Binds the complete editor release to completed exact-package and actual guest recovery checks.
# ABOUTME: Refuses mixed evidence and records daily and public acceptance as later gates.
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


build = load('candidate-build.json')
commit = '04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
archive_sha = 'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
assert build['head'] == commit and build['version'] == '0.5.0'
assert build['archive_sha256'] == digest(build['archive']) == archive_sha
assert Path(build['archive']).stat().st_size == build['archive_bytes'] == 206859436
integration = load('integration-04efe633.json')
native = load('native-sealed-04efe633.json')
for receipt in (integration, native):
    assert receipt['exit_code'] == 0 and receipt['package_commit'] == commit
    assert receipt['archive_sha256'] == archive_sha
assert integration['archive_files_match_before'] and integration['archive_files_match_after']
output = text('integration-04efe633.stderr')
assert 'Ran 821 tests' in output and output.rstrip().endswith('OK')
assert 'ResourceWarning' not in output and 'skipped' not in output
assert text('integration-04efe633.done').strip() == '0'
assert '38 files, 716 tests passed, 0 failed (100% complete)' in text('native-sealed-04efe633.stdout')
assert not text('native-sealed-04efe633.stderr')
assert text('native-sealed-04efe633.done').strip() == '0'
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
assert 'Ran 63 tests' in text('review-targeted.stderr') and text('review-targeted.stderr').rstrip().endswith('OK')
assert 'skipped' not in text('review-targeted.stderr')
probes = load('review-probes.stdout')
assert probes['status'] == 'PASS' and probes['cases'] == 13 and len(probes['results']) == 13
assert all(row['status'] == 'PASS' for row in probes['results'])
review = out.parents[1] / 'agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md'
assert 'CLEAR for the reviewed product change.' in review.read_text() and commit in review.read_text()

fresh = passed('stock-first-install.json')
assert fresh['production_guest_changed'] is False
manager = passed('stock-manager-install.json')
bootstrap = passed('manager-bootstrap.json')
assert fresh['commit'] == manager['commit'] == bootstrap['ref'] == commit
assert fresh['package_sha256'] == archive_sha
assert fresh['authenticated_owner_verified'] and fresh['selected_model_and_tiers_preserved']
assert fresh['active']['version'] == '0.5.0' and fresh['active']['verification'] == 'verified'
assert fresh['active']['commit'] == commit and fresh['active']['package_sha256'] == archive_sha
assert manager['http_status'] == 200 and manager['manager_file_count'] == bootstrap['manager_files_verified'] == 21
assert manager['endpoint'] == '/api/dashboard/agent-plugins/install' and manager['authenticated_owner_verified']
assert not manager['lifeos_installed'] and not fresh['personal_data_imported_or_reset']
assert fresh['services']['hermes-dashboard.service']['ActiveState'] == 'active'
assert all(fresh['services'][unit]['ActiveState'] == 'inactive' for unit in ('hermes-gateway.service','com.lifeos.pulse.service'))
stock = load('stock-source.json')
assert stock['commit'] == build['hermes_base'] and stock['patched'] is False
editor = passed('installed-editor-verification.json')
browser = passed('browser-editor-verification.json')
compiled = passed('compiled-page-identity.json')
for receipt in (editor, browser, compiled):
    assert receipt['program_commit'] == commit and receipt['archive_sha256'] == archive_sha
assert editor['declared_files'] == 24 and editor['authenticated_owner_verified']
assert editor['anonymous_read_status'] == 401 and editor['owner_read_status'] == editor['owner_save_status'] == 200
assert editor['private_save_mode'] == '0600' and editor['stale_save_status'] == 409 and editor['sealed_read_status'] == 403
assert editor['actual_remount_status'] == 200 and editor['remounted_identity_present'] and editor['configuration_values_preserved']
assert browser['owner_ui_save'] and browser['persisted_marker_verified'] and browser['actual_ui_remount_status'] == 200
assert browser['stale_ui_save_status'] == 409 and browser['concurrent_owner_bytes_preserved']
assert browser['after_logout_ui_save_status'] == browser['after_logout_overview_status'] == 401
assert browser['after_logout_textarea_absent'] and browser['after_logout_save_absent'] and browser['after_logout_owner_surface_withheld']
assert compiled['archived_page_sha256'] == compiled['installed_page_sha256'] == compiled['served_page_sha256']
assert compiled['served_matches_installed'] and compiled['installed_matches_archived']
with tarfile.open(build['archive']) as archive:
    html = archive.extractfile('lifeos/LifeOS/install/LIFEOS/PULSE/Observability/out/assistant.html').read()
assert hashlib.sha256(html).hexdigest() == compiled['archived_page_sha256']

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
    assert receipt['active']['version'] == '0.5.0' and receipt['active']['commit'] == commit
    assert receipt['active']['package_sha256'] == archive_sha and receipt['active']['verification'] == 'verified'
assert restored['active']['version'] == '0.3.1' and restored['active']['verification'] == 'verified'
assert restored['active']['commit'] == '9af633252004a0ac8dd780d5fc12e9644f97bb0c'
assert restored['active']['package_sha256'] == '2aada985dd26dee4ffb4da1d3348c43c76cff2e697d04028cfbba9d6f1b11a24'
interrupted = load('interrupted-action.json')
assert interrupted['exit_status'] == 73 and interrupted['unit_collected'] and interrupted['authenticated_owner_verified']
assert interrupted['candidate_commit'] == commit and interrupted['native_mount_required'] is True
states = passed('synthetic-operation-states.json')['operations']
assert len(states) == 3
for row in states:
    assert row['program_commit'] == commit and row['archive_sha256'] == archive_sha
    assert row['account_home'] == '/home/lifeos-hermes' and row['native_home'] != row['account_home']
recovered = next(row for row in states if row['operation'] == interrupted['operation'])
assert recovered['state'] == 'rolled_back' and recovered['program_state'] == 'restored'
assert states[0]['state'] == 'rolled_back' and states[0]['program_state'] == 'restored'
operation = '2bef1668a01e499096f1b855a2d9eac7'
assert states[-1]['operation'] == operation and states[-1]['state'] == states[-1]['program_state'] == 'applied'

whole = passed('bound-whole-guest-recovery.json')
coverage = passed('bound-whole-guest-program-coverage.json')
artifacts = passed('bound-whole-guest-artifact-coverage.json')
captured = passed('source-program-artifact-capture.json')
backup_operations = load('source-backup-operations.json')
assert {'backup-source', 'resume-source'} <= {row['label'] for row in backup_operations if row['exit_code'] == 0}
assert all(row['exit_code'] == 0 for row in backup_operations)
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
assert commands['restore'] == ['pct', 'restore', '110', whole['archive'], '--storage', 'lifeos-050-tests',
    '--rootfs', 'lifeos-050-tests:120', '--unprivileged', '1', '--onboot', '0', '--hostname', 'lifeos-050-recovery']
assert commands['disconnect'] == ['pct', 'set', '110', '--delete', 'net0', '--onboot', '0',
    '--tags', 'disposable;lifeos-050-recovery']
for label, verb in (('mount', 'mount'), ('unmount', 'unmount'), ('boot-isolated', 'start')):
    assert commands[label] == ['pct', verb, '110']
assert commands['shutdown-restore'] == ['pct', 'shutdown', '110', '--timeout', '90']
assert commands['destroy-disposable'] == ['pct', 'destroy', '110', '--purge', '1']
selected_python = '/home/lifeos-hermes/.hermes/.lifeos-releases/' + operation + '/python-environment/bin/python'
execution = ['pct', 'exec', '110', '--', 'runuser', '-u', 'lifeos-hermes', '--', selected_python, '-B']
operator_path = '/home/lifeos-hermes/releases/qualification-0.5.0/'
assert commands['verify-history'] == execution + [operator_path + 'history_guest_recovery.py',
    'verify', '/home/lifeos-hermes/.hermes/.lifeos-releases/' + operation + '/package']
assert commands['verify-program-artifacts'] == execution + [operator_path + 'program_artifact_receipt.py', 'verify', operation]
assert commands['verify-stable-programs'] == execution + [operator_path + 'verify_restored_programs.py', operation]
source_commands = {row['label']: row['command'] for row in backup_operations}
assert len(source_commands) == len(backup_operations)
assert source_commands['backup-source'] == ['vzdump', '111', '--storage', 'PBS-01', '--mode', 'stop',
    '--notes-template', 'LifeOS 0.5.0 managed release recovery']
source_execution = ['pct', 'exec', '111', '--', 'runuser', '-u', 'lifeos-hermes', '--', selected_python, '-B']
assert source_commands['capture-program-artifacts'] == source_execution + [operator_path + 'program_artifact_receipt.py', 'capture', operation]
assert source_commands['drain-source'] == source_commands['resume-source'] == source_execution + ['-']
for receipt in (whole, coverage):
    assert receipt['source_guest'] == 111 and receipt['restored_guest'] == 110
    assert receipt['version'] == '0.5.0'
assert whole['production_guest_changed'] is False
assert whole['network_disconnected'] and whole['application_services_masked']
assert {row['case'] for row in whole['cases']} == {'baseline', 'interrupted', 'later-edit'}
assert len(whole['cases']) == 3 and all(row['status'] == 'PASS' for row in whole['cases'])
for row in whole['cases']:
    assert row['archive_and_live_group_verified'] is True
    assert row['later_edit_refused'] is (row['case'] == 'later-edit')
    assert row['restored_files'] == (51 if row['case'] == 'baseline' else 55)
assert coverage['program_targets'] == 221 and coverage['application_services_masked']
assert coverage['native_mount_required'] and coverage['native_mount_targets'] == 8
assert coverage['owner_memory_configuration_verified'] and coverage['credential_file_bytes_preserved']
assert artifacts['artifacts'] == 64401 and artifacts['regular_files'] == 57963
assert whole['runtime_artifact_coverage'] == artifacts
frontend = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')
assert digest(frontend) == 'e7c93e754de99b6ec66ae17ae313377dc513104da2776a099c391a7aab347bec'
reboot = passed('reboot-verification.json')
assert reboot['source_guest'] == 111 and reboot['production_guest_changed'] is False
assert reboot['operation'] == operation and reboot['program_commit'] == commit and reboot['archive_sha256'] == archive_sha
assert reboot['boot_identity_changed'] and reboot['selected_programs_and_services_verified'] and reboot['model_mapping_and_synthetic_memory_preserved']
development = passed('development-verification.json')
assert development['server'] == 'development' and development['active_identity']['commit'] == commit
assert development['active_identity']['version'] == '0.5.0' and development['active_identity']['package_sha256'] == archive_sha
assert development['active_identity']['verification'] == 'verified'
assert development['model_and_tiers_preserved'] and development['credential_file_bytes_preserved'] and development['memory_configuration_bytes_preserved']
assert set(development['services']) == {'hermes-dashboard.service','hermes-gateway.service','com.lifeos.pulse.service'}
assert all(value == {'active':True,'home_preserved':True,'profile_preserved':True} for value in development['services'].values())
turn = passed('development-owner-turn-verification.json')
assert turn['actual_write_and_fresh_conversation_read_verified'] and len(set(turn['sessions'])) == 2
assert turn['verification_active_identity'] == {key: development['active_identity'][key] for key in ('version','commit','package_sha256')}
certificate = {'format': 1, 'status': 'QUALIFIED', 'production_qualified': True,
    'version': '0.5.0', 'program_commit': commit, 'archive_sha256': archive_sha,
    'archive_bytes': build['archive_bytes'], 'hermes_dashboard_sha256': digest(frontend),
    'hermes_base': build['hermes_base'], 'lifeos_base': build['lifeos_base'],
    'hermes_patch_count': build['hermes_patch_count'], 'lifeos_patch_count': build['lifeos_patch_count'],
    'integration_tests': 821, 'native_tests': 716, 'native_test_files': 38, 'focused_review_tests': 63, 'independent_additional_probes': 13,
    'qualification_scope': 'Exact archive regression, stock installation, owner-governed editor, native update and rollback, worker-exit recovery, reboot, development memory turns, and disconnected whole-guest restore',
    'native_service_home_and_model_mapping_preserved': True,
    'whole_guest_history_recovery': whole, 'whole_guest_program_coverage': coverage,
    'whole_guest_runtime_coverage': artifacts,
    'clean_stock_installation_verified': True, 'governed_editor_installed_verified': True,
    'governed_editor_browser_verified': True, 'development_owner_turn_verified': True,
    'older_manager_bootstrap_required': True,
    'source_review_report_sha256': digest(review),
    'qualification_receipt_sha256': {name: digest(out / name) for name in sorted(used)},
    'daily_promotion_verified': False, 'automatic_morning_observed': False,
    'public_default_url_replay_for_050': 'Pending public publication',
    'build_manifest_note': 'The immutable package manifest records build-time state. This certificate records completed corrective qualification.'}
target = out / 'RELEASE-CERTIFICATE.json'
assert not target.exists(), 'The release certificate already exists'
target.write_text(json.dumps(certificate, indent=2) + '\n')
print(json.dumps({'status': 'QUALIFIED', 'program_commit': commit,
                  'certificate_sha256': digest(target)}, indent=2))
