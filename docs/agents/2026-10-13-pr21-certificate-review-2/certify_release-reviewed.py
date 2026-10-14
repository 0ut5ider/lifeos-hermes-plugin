# ABOUTME: Binds stable release assets to completed archive, installation, development, and restore receipts.
# ABOUTME: Refuses incomplete or stale evidence and leaves daily promotion as a separate release decision.
import hashlib
import json
from pathlib import Path
import re
import tarfile

out = Path(__file__).resolve().parent
used = set()


def load(name):
    used.add(name)
    return json.loads((out / name).read_bytes())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def passed(name):
    receipt = load(name)
    assert receipt['status'] == 'PASS', name
    return receipt


def text(name):
    used.add(name)
    return (out / name).read_text()


build = load('stable-build.json')
commit = '87205092832c550a09fce6e1cb3ca944fdb69a8c'
archive_sha = '76c1c10e82ce75f86858a2cd27ae609f5f7eb8a8bc79612d94df6f95f45136a4'
assert build['head'] == commit and build['version'] == '0.4.2'
assert build['archive_sha256'] == archive_sha and digest(build['archive']) == archive_sha
assert Path(build['archive']).stat().st_size == build['archive_bytes'] == 119149672
active = {'version': '0.4.2', 'commit': commit, 'package_sha256': archive_sha}

integration = load('integration-archive-bound-87205092.json')
assert integration['exit_code'] == 0 and integration['package_commit'] == commit
assert integration['archive_sha256'] == archive_sha
assert integration['archive_files_match_before'] and integration['archive_files_match_after']
output = text('integration-archive-bound-87205092.stderr')
assert re.search(r'Ran 675 tests', output) and output.rstrip().endswith('OK')
assert 'skipped' not in output and 'ResourceWarning' not in output
assert text('integration-archive-bound-87205092.done').strip() == '0'

native = load('native-sealed-87205092.json')
assert native['exit_code'] == 0 and native['package_commit'] == commit
assert native['archive_sha256'] == archive_sha and native['archived_source_files_unchanged'] is True
with tarfile.open(build['archive']) as archive:
    source_bytes = archive.extractfile('hermes/hermes-source-manifest.json').read()
assert native['source_manifest_sha256'] == hashlib.sha256(source_bytes).hexdigest()
assert native['source_tree_sha256'] == json.loads(source_bytes)['tree_sha256']
assert native['bun_version'] == '1.4.3'
assert native['bun_binary_sha256'] == '7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b'
assert '38 files, 716 tests passed, 0 failed (100% complete)' in text('native-sealed-87205092.stdout')
assert not text('native-sealed-87205092.stderr')
assert text('native-sealed-87205092.done').strip() == '0'

fresh = passed('fresh-native-github-manager-install.json')
assert fresh['guest'] == 109 and fresh['force_reinstall'] is False
assert fresh['explicit_branch_or_commit_selected'] is False and fresh['native_install_metadata_pinned'] is False
assert fresh['post_full_package_manager_matches_candidate'] == commit
assert fresh['post_full_package_all_manager_files_private'] is True
prepared = passed('fresh-preparation.json')['preparation']
assert {key: prepared[key] for key in active} == active
ownership = passed('fresh-ownership-activation.json')
assert ownership['operation'] == prepared['identifier'] and ownership['authenticated_owner_verified'] is True
assert ownership['personal_data_imported'] is False and ownership['selected_model_and_tiers_preserved'] is True
for name in ('release-owner-turn-verification.json', 'development-owner-turn-verification.json'):
    owner = passed(name)
    assert owner['actual_write_and_fresh_conversation_read_verified'] is True
    assert len(set(owner['sessions'])) == 2 and owner['synthetic_data_only'] is True

update = passed('development-update.json')
rollback = passed('development-rollback.json')
interrupted = passed('development-interruption-exit.json')
recovery = passed('development-interruption-recovery.json')
final = passed('development-final-update.json')
assert update['active_identity'] == final['active_identity'] == active
assert update['operation'] == rollback['operation']
assert interrupted['operation'] == recovery['operation']
assert interrupted['candidate_commit'] == commit and interrupted['archive_sha256'] == archive_sha
assert interrupted['service']['ExecMainStatus'] == '73' and interrupted['actual_worker_exit_verified'] is True
assert interrupted['real_entrypoint_mask_used'] is True
assert interrupted['operation_state'] == 'applying' and interrupted['program_transaction_state'] == 'applied'
assert rollback['active_identity'] == recovery['active_identity']
for receipt in (update, rollback, recovery, final):
    assert receipt['model_selection_sha256'] == update['model_selection_sha256']
    assert receipt['daily_server_changed'] is False
    assert all(unit['ActiveState'] == 'active' and unit['SubState'] == 'running' for unit in receipt['services'].values())
assert rollback['operation_state'] == recovery['operation_state'] == 'rolled_back'
assert rollback['program_transaction_state'] == recovery['program_transaction_state'] == 'restored'

boot = passed('development-boot.json')
assert boot['operation'] == final['operation'] and boot['active_identity'] == active
assert boot['boot_id'] != boot['before_boot_id'] and boot['manual_service_start_after_reboot'] is False
assert all(unit['ActiveState'] == 'active' and unit['UnitFileState'] == 'enabled' and unit['NRestarts'] == '0'
           for unit in boot['units'].values())
audience = passed('development-private-discord-configuration.json')
assert audience['private_audience_verified'] is True
assert set(audience['readers']) == {'708089927468056648', '1554102173535703140'}
discord = passed('development-discord-delivery.json')
assert discord['memory_fact_supplied_in_discord_request'] is False
assert discord['native_cli_memory_receipts_verified_separately'] is True
assert discord['channel'] == '1559717651817697361' and discord['daily_server_changed'] is False
jobs = load('native-jobs-original-source-refusal.json')['jobs'][:2]
jobs += load('native-jobs-atlas-completed-algorithm-refused.json')['jobs'][:1]
jobs += passed('native-jobs-complete-algorithm.json')['jobs']
assert {job['job'] for job in jobs} == {'user-index', 'conduit-insight', 'atlas-insights', 'algorithm-summaries'}
assert all(job['exit_code'] == 0 and job['stderr_bytes'] == 0 and job['receipt_status'] == 'completed' for job in jobs)

whole = passed('whole-guest-recovery.json')
coverage = passed('whole-guest-program-coverage.json')
artifacts = passed('whole-guest-artifact-coverage.json')
captured = passed('program-artifact-capture.json')
assert text('whole-guest-process.done').strip() == '0'
operations = load('whole-guest-operations.json')
required = {'backup-source', 'resume-source', 'restore', 'disconnect', 'boot-isolated', 'verify-history',
            'verify-program-artifacts', 'verify-stable-programs', 'shutdown-restore', 'destroy-disposable'}
assert required <= {row['label'] for row in operations}
assert all(row['exit_code'] == 0 for row in operations)
for receipt in (whole, coverage, artifacts, captured):
    assert receipt['program_commit'] == commit and receipt['archive_sha256'] == archive_sha
    assert receipt['operation'] == final['operation']
for receipt in (whole, coverage):
    assert receipt['version'] == '0.4.2'
    assert receipt['source_guest'] == 101 and receipt['restored_guest'] == 110
assert whole['archive'] == coverage['backup_archive'] and whole['archive'].startswith('PBS-01:backup/ct/101/')
assert whole['network_disconnected'] is True and whole['application_services_masked'] is True
assert {row['case'] for row in whole['cases']} == {'baseline', 'interrupted', 'later-edit'}
assert len(whole['cases']) == 3 and all(row['status'] == 'PASS' for row in whole['cases'])
assert coverage['program_targets'] == 10 and coverage['native_mount_targets'] == 8
assert coverage['network_disconnected'] is True and coverage['application_services_masked'] is True
assert coverage['owner_memory_configuration_verified'] is True
assert artifacts['private_map_sha256'] == captured['private_map_sha256']
assert artifacts['artifacts'] == captured['artifacts'] == 64268
assert artifacts['regular_files'] == captured['regular_files'] == 57843
assert whole['runtime_artifact_coverage'] == artifacts

frontend = load('frontend-build.json')
assert frontend['status'] == 'PASS' and digest(frontend['archive']) == frontend['sha256']
assert Path(frontend['archive']).stat().st_size == frontend['bytes']
certificate = {'format': 1, 'status': 'QUALIFIED', 'production_qualified': True, 'version': '0.4.2',
    'program_commit': commit, 'archive_sha256': archive_sha, 'archive_bytes': build['archive_bytes'],
    'hermes_dashboard_sha256': frontend['sha256'],
    'hermes_base': build['hermes_base'], 'lifeos_base': build['lifeos_base'],
    'hermes_patch_count': build['hermes_patch_count'], 'lifeos_patch_count': build['lifeos_patch_count'],
    'bun_version': '1.4.3', 'frozen_native_locks_unchanged': True,
    'integration_tests': 675, 'native_tests': 716, 'native_test_files': 38,
    'clean_web_installation_verified': True, 'synthetic_memory_ownership_verified': True,
    'installed_development_verified': True, 'development_interruption_recovery_verified': True,
    'development_program_rollback_verified': True, 'development_boot_verified': True,
    'native_owner_jobs_verified': [job['job'] for job in jobs],
    'discord_specific_tool_receipt_verified': discord['specific_discord_tool_receipt_verified'],
    'whole_guest_history_recovery': whole, 'whole_guest_program_coverage': coverage,
    'whole_guest_runtime_coverage': artifacts,
    'qualification_receipt_sha256': {name: digest(out / name) for name in sorted(used)},
    'daily_promotion_verified': False, 'automatic_morning_observed': False,
    'public_latest_acceptance': 'Pending publication replay in a separate receipt',
    'build_manifest_note': 'The immutable candidate manifest records build-time state. This certificate records completed release qualification.'}
target = out / 'RELEASE-CERTIFICATE.json'
assert not target.exists(), 'The release certificate already exists'
target.write_text(json.dumps(certificate, indent=2) + '\n')
print(json.dumps({'status': 'QUALIFIED', 'program_commit': commit, 'certificate_sha256': digest(target)}, indent=2))
