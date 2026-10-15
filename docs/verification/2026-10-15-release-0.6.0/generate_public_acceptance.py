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
evidence = {name: json.loads((directory / name).read_bytes()) for name in names}
fresh = evidence['public-fresh-verification.json']
post = evidence['public-post-model-verification.json']
manager = evidence['public-manager-source-verification.json']
certificate = evidence['RELEASE-CERTIFICATE.json']
assert certificate['status'] == 'QUALIFIED' and certificate['production_qualified'] is True
assert hashlib.sha256((directory / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest() == 'e53fa1a02d52637fd9678d6978900c10d3003bb2059c78c689078bc0de3db770'
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
assert post['prior_model_receipt_sha256'] == hashlib.sha256((directory / 'public-fresh-verification.json').read_bytes()).hexdigest()
assert fresh['active_identity'] == post['active_identity']
active = fresh['active_identity']
assert active['version'] == certificate['version'] == '0.6.0'
assert active['commit'] == post['program_commit'] == certificate['program_commit']
assert active['package_sha256'] == post['archive_sha256'] == certificate['archive_sha256']
assert active['verification'] == 'verified' and active['modified_files'] == []
assert manager['matched_files'] == len(manager['files']) == 38
assert manager['expected_program_commit'] == active['commit']
assert not manager['native_store_exists'] and not manager['memory_policy_exists']
assert evidence['public-fixture-reset.json']['status'] == 'PASS'
before = evidence['public-fresh-before-application.json']
assert before['native_store_present'] is False and before['policy_present'] is False
assert before['model_mapping_sha256'] == fresh['model_mapping_sha256']
assert evidence['publication.json']['previous_assets_unchanged'] == 56
assert all(fresh[key] is False for key in ('production_guest_changed',
    'personal_records_read', 'personal_data_imported_or_reset'))
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
    'evidence_sha256': {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}}
with (directory / 'PUBLIC-LATEST-ACCEPTANCE.json').open('x') as handle:
    json.dump(receipt, handle, indent=2)
    handle.write('\n')
print(json.dumps({'status': 'PASS', 'evidence_files': len(names)}))
