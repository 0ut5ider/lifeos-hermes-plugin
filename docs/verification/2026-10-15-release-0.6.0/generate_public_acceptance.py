# ABOUTME: Binds the public web installation and post-model receipts to the qualified release.
# ABOUTME: Creates a supplementary acceptance checkpoint without replacing the initial certificate.
import hashlib
import json
from pathlib import Path
import sys

if sys.flags.optimize:
    raise RuntimeError('Acceptance requires assertions')
directory = Path(__file__).resolve().parent
names = ('public-fixture-reset.json', 'public-fresh-before-application.json',
    'public-manager-source-verification.json', 'public-plugin-scan-confirmation.json',
    'public-fresh-verification.json', 'public-post-model-verification.json',
    'publication.json', 'deployed-checkpoint.json', 'RELEASE-CERTIFICATE.json')
raw = {name: (directory / name).read_bytes() for name in names}
evidence = {name: json.loads(value) for name, value in raw.items()}
fresh = evidence['public-fresh-verification.json']
post = evidence['public-post-model-verification.json']
manager = evidence['public-manager-source-verification.json']
certificate = evidence['RELEASE-CERTIFICATE.json']
assert certificate['status'] == 'QUALIFIED' and certificate['production_qualified'] is True
assert hashlib.sha256(raw['RELEASE-CERTIFICATE.json']).hexdigest() == 'e53fa1a02d52637fd9678d6978900c10d3003bb2059c78c689078bc0de3db770'
assert fresh['status'] == post['status'] == manager['status'] == 'PASS'
assert fresh['kind'] == 'public' and fresh['guest'] == 112
assert fresh['operation'] == post['operation'] == 'a8486ae6890a41ceaf29202cb5dce463'
assert fresh['public_catalog_certificate_verified'] is True
assert fresh['actual_model_round_trip'] is True and fresh['model_turn_executed'] is True
assert fresh['model_session'] == post['model_session'] and fresh['model_session']
assert fresh['tool_names'] == [] and fresh['sealed_program_targets'] == 11
assert fresh['fresh_installation'] is True and fresh['native_mount_required'] is True
assert fresh['selected_model_and_tiers_preserved'] is True
assert post['sealed_programs_verified_after_model'] is True
assert post['selected_model_and_tiers_unchanged_after_model'] is True
assert post['prior_model_receipt_sha256'] == hashlib.sha256(raw['public-fresh-verification.json']).hexdigest()
assert fresh['active_identity'] == post['active_identity']
active = fresh['active_identity']
assert active['version'] == certificate['version'] == '0.6.0'
assert active['commit'] == post['program_commit'] == certificate['program_commit']
assert active['package_sha256'] == post['archive_sha256'] == certificate['archive_sha256']
assert active['verification'] == 'verified' and active['modified_files'] == []
assert manager['matched_files'] == len(manager['files']) == 38
assert manager['expected_program_commit'] == active['commit']
assert hashlib.sha256(json.dumps(manager['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() == 'deff760a90277fdf8511ffa1a8415f000fce376f4ccd0a0db79c7df4fa2be1a1'
url = 'https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager'
assert manager['source'] == url
assert manager['native_store_exists'] is False and manager['memory_policy_exists'] is False
reset = evidence['public-fixture-reset.json']
assert reset['status'] == 'PASS' and reset['guest'] == 112
assert reset['hostname'] == 'lifeos-portability-release-test'
assert reset['only_owned_synthetic_fixture_reset'] is True and reset['production_changed'] is False
assert reset['operations'] == [
    {'command': ['pct', 'shutdown', '112', '--timeout', '90'], 'exit_code': 0},
    {'command': ['pct', 'rollback', '112', 'portability-pristine-20261015'], 'exit_code': 0},
    {'command': ['pct', 'start', '112'], 'exit_code': 0}]
before = evidence['public-fresh-before-application.json']
assert before['native_store_present'] is False and before['policy_present'] is False
assert before['guest'] == 112 and before['only_owned_pristine_fixture'] is True
assert before['public_catalog_preparation'] is True
assert before['model_mapping_sha256'] == fresh['model_mapping_sha256']
scan = evidence['public-plugin-scan-confirmation.json']
assert scan['status'] == 'PASS_WITH_EXPLICIT_NATIVE_CONFIRMATION'
assert scan['source'] == url and scan['guest'] == 112
assert scan['initial_http_status'] == 400 and scan['native_scan_verdict'] == 'CAUTION'
assert scan['findings'] == 18 and scan['initial_installation_refused'] is True
assert scan['native_ui_control_used'] == 'Force reinstall (delete existing folder first)'
assert scan['target_was_empty_before_confirmation'] is True and scan['scanner_disabled'] is False
assert scan['successful_http_response_retained'] is False
deployment = evidence['deployed-checkpoint.json']
assert deployment['status'] == 'PASS'
assert all(deployment[key] is False for key in ('release_work_changed_development',
    'release_work_changed_daily', 'personal_data_imported_or_reset'))
for name, address in (('development', '192.168.8.252'), ('daily', '192.168.8.253')):
    deployed = deployment[name]
    assert deployed['address'] == address and deployed['version'] == '0.5.0'
    assert deployed['verification'] == 'verified' and deployed['modified_files'] == []
    assert deployed['commit'] == '04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
    assert deployed['package_sha256'] == 'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
publication = evidence['publication.json']
assert publication['status'] == 'PASS' and publication['tag'] == 'v0.6.0'
assert publication['release_url'] == 'https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.6.0'
assert publication['program_commit'] == active['commit'] and publication['previous_assets_unchanged'] == 56
assets = publication['initial_assets']
assert set(assets) == {'v0.6.0/0.6.0-c86b5887.tgz', 'v0.6.0/hermes-dashboard.tgz',
    'v0.6.0/RELEASE-CERTIFICATE.json'}
assert assets['v0.6.0/0.6.0-c86b5887.tgz']['digest'] == 'sha256:' + certificate['archive_sha256']
assert assets['v0.6.0/0.6.0-c86b5887.tgz']['size'] == certificate['archive_bytes']
assert assets['v0.6.0/hermes-dashboard.tgz']['digest'] == 'sha256:' + certificate['hermes_dashboard_sha256']
assert assets['v0.6.0/RELEASE-CERTIFICATE.json']['digest'] == 'sha256:' + hashlib.sha256(raw['RELEASE-CERTIFICATE.json']).hexdigest()
assert assets['v0.6.0/RELEASE-CERTIFICATE.json']['size'] == len(raw['RELEASE-CERTIFICATE.json'])
assert all(fresh[key] is False for key in ('production_guest_changed',
    'personal_records_read', 'personal_data_imported_or_reset'))
assert post['production_guest_changed'] is False
receipt = {'format': 1, 'status': 'PASS', 'version': active['version'],
    'program_commit': active['commit'], 'package_sha256': active['package_sha256'],
    'public_default_github_url': manager['source'], 'default_ref_used': True,
    'latest_stable_selected_from_public_catalog': True,
    'actual_native_ui_install_review_apply_verified': True,
    'operation': fresh['operation'], 'fresh_owner_browser_final_status': 'applied',
    'manager_files_verified': 38, 'sealed_program_groups_verified': 11,
    'model_and_tiers_preserved': True, 'real_model_turn_on_public_fixture': True,
    'post_model_integrity_verified': True, 'initial_certificate_unchanged': True,
    'native_security_scan_confirmation_required': True,
    'production_guest_changed': False, 'personal_records_exported': False,
    'personal_data_imported_or_reset': False,
    'scope': 'Public latest installation and an actual model reply. Personal memory activation and production promotion remain separate owner actions.',
    'evidence_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}}
with (directory / 'PUBLIC-LATEST-ACCEPTANCE.json').open('x') as handle:
    json.dump(receipt, handle, indent=2)
    handle.write('\n')
print(json.dumps({'status': 'PASS', 'evidence_files': len(names)}))
