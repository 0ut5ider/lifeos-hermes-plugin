# ABOUTME: Repeats the PR30 receipt checks and tests decisive evidence fields individually.
# ABOUTME: Keeps all generated receipts and mutations in temporary directories.
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[3]
output = Path(__file__).resolve().parent
directory = repo / 'docs/verification/2026-10-15-release-0.6.0'
head = 'd0d79d67e294ba5c3e760febd5a0b7e313e8a99f'
original = repo / 'docs/agents/2026-10-15-pr30-public-acceptance-review/check_public_acceptance.py'
checks = []
runs = []


def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})


def git(*arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments])


check('exact_closure_head', git('rev-parse', 'HEAD').decode().strip() == head)
with tempfile.TemporaryDirectory(prefix='pr30-original-controls-', dir=output) as location:
    checker = Path(location) / 'check_public_acceptance.py'
    source = original.read_text()
    assert source.count('9c886816255bf1226bc3aa606107d48635b281a3') == 1
    checker.write_text(source.replace('9c886816255bf1226bc3aa606107d48635b281a3', head))
    repeat = subprocess.run([sys.executable, '-W', 'error', '-B', str(checker), '--repo', str(repo),
        '--output', str(output / 'original-controls-repeat')], capture_output=True, text=True)
    result = json.loads((output / 'original-controls-repeat/review-checks.json').read_bytes())
    check('original_19_checks_with_only_expected_head_updated', repeat.returncode == 0 and
        result['passed'] == result['total'] == 19 and repeat.stderr == '',
        {'stdout': repeat.stdout, 'stderr': repeat.stderr})

manager = json.loads((directory / 'public-manager-source-verification.json').read_bytes())
actual_map = {name: hashlib.sha256(git('show',
    'c86b5887b899ca779afbb217c33843e1ee12c381:optional/lifeos_release_manager/' + name)).hexdigest()
    for name in manager['files']}
canonical_digest = hashlib.sha256(json.dumps(actual_map, sort_keys=True,
    separators=(',', ':')).encode()).hexdigest()
check('canonical_38_file_map_matches_actual_qualified_git_objects', len(actual_map) == 38 and
    actual_map == manager['files'] and canonical_digest ==
    'deff760a90277fdf8511ffa1a8415f000fce376f4ccd0a0db79c7df4fa2be1a1', canonical_digest)
check('generator_binds_canonical_map_digest', canonical_digest in
    (directory / 'generate_public_acceptance.py').read_text())
check('initial_certificate_bytes_unchanged', (directory / 'RELEASE-CERTIFICATE.json').read_bytes() ==
    git('show', 'd5386d76:docs/verification/2026-10-15-release-0.6.0/RELEASE-CERTIFICATE.json'))
check('supplementary_receipt_bytes_unchanged', (directory / 'PUBLIC-LATEST-ACCEPTANCE.json').read_bytes() ==
    git('show', '9c886816:docs/verification/2026-10-15-release-0.6.0/PUBLIC-LATEST-ACCEPTANCE.json'))
check('no_product_changes_from_merged_base', not git('diff', '--name-only', 'd5386d76..' + head,
    '--', 'lifeos_hook_bridge', 'optional', 'VERSION', 'scripts', 'tests').strip())
check('post_model_operator_unchanged', (directory / 'verify_public_after_model.py').read_bytes() ==
    git('show', '9c886816:docs/verification/2026-10-15-release-0.6.0/verify_public_after_model.py'))
immutability = json.loads((directory / 'public-asset-immutability-before-acceptance.json').read_bytes())
check('safe_asset_preservation_checkpoint', immutability == {'status': 'PASS',
    'earlier_assets_preserved': 56, 'initial_060_assets_preserved': 3,
    'latest_stable': 'v0.6.0', 'supplementary_asset_published': False})
check('portability_docs_report_published_release', 'unreleased' not in
    (repo / 'docs/memory-portability.md').read_text().lower())

fields = {
    'public-plugin-scan-confirmation.json': {
        'status': 'FAIL', 'source': 'https://example.invalid/private', 'guest': 102,
        'initial_http_status': 200, 'native_scan_verdict': 'SAFE', 'findings': 0,
        'initial_installation_refused': False, 'native_ui_control_used': 'none',
        'target_was_empty_before_confirmation': False, 'scanner_disabled': True,
        'successful_http_response_retained': True},
    'deployed-checkpoint.json': {
        'status': 'FAIL', 'release_work_changed_development': True,
        'release_work_changed_daily': True, 'personal_data_imported_or_reset': True},
    'publication.json': {'status': 'FAIL', 'tag': 'v0.5.0',
        'release_url': 'https://example.invalid/private', 'program_commit': '0' * 40,
        'previous_assets_unchanged': 55, 'initial_assets': {}},
    'public-manager-source-verification.json': {'status': 'FAIL', 'source': 'https://example.invalid/private',
        'matched_files': 37, 'expected_program_commit': '0' * 40,
        'native_store_exists': True, 'memory_policy_exists': True},
    'public-fixture-reset.json': {'status': 'FAIL', 'guest': 102, 'hostname': 'daily',
        'only_owned_synthetic_fixture_reset': False, 'production_changed': True,
        'operations': []},
    'public-fresh-before-application.json': {'native_store_present': True, 'policy_present': True,
        'guest': 102, 'only_owned_pristine_fixture': False, 'public_catalog_preparation': False,
        'model_mapping_sha256': '0' * 64},
    'public-post-model-verification.json': {'status': 'FAIL', 'operation': '0' * 32,
        'program_commit': '0' * 40, 'archive_sha256': '0' * 64,
        'prior_model_receipt_sha256': '0' * 64, 'model_session': 'wrong',
        'sealed_programs_verified_after_model': False,
        'selected_model_and_tiers_unchanged_after_model': False,
        'production_guest_changed': True},
}
mutations = [(name, (field,), value) for name, values in fields.items() for field, value in values.items()]
for guest in ('development', 'daily'):
    mutations.extend(('deployed-checkpoint.json', (guest, field), value) for field, value in {
        'address': '192.168.8.248', 'version': '0.6.0', 'verification': 'unverified',
        'modified_files': ['changed'], 'commit': '0' * 40, 'package_sha256': '0' * 64}.items())
for asset in ('v0.6.0/0.6.0-c86b5887.tgz', 'v0.6.0/hermes-dashboard.tgz',
        'v0.6.0/RELEASE-CERTIFICATE.json'):
    mutations.append(('publication.json', ('initial_assets', asset, 'digest'), 'sha256:' + '0' * 64))
for asset in ('v0.6.0/0.6.0-c86b5887.tgz', 'v0.6.0/RELEASE-CERTIFICATE.json'):
    mutations.append(('publication.json', ('initial_assets', asset, 'size'), 0))
mutations.append(('public-manager-source-verification.json', ('files', 'plugin.yaml'), '0' * 64))
for name, path, value in mutations:
    with tempfile.TemporaryDirectory(prefix='pr30-field-control-') as location:
        folder = Path(location)
        for receipt in json.loads((directory / 'PUBLIC-LATEST-ACCEPTANCE.json').read_bytes())['evidence_sha256']:
            shutil.copy2(directory / receipt, folder)
        shutil.copy2(directory / 'generate_public_acceptance.py', folder)
        changed = json.loads((folder / name).read_bytes())
        parent = changed
        for component in path[:-1]:
            parent = parent[component]
        parent[path[-1]] = copy.deepcopy(value)
        (folder / name).write_text(json.dumps(changed, indent=2) + '\n')
        result = subprocess.run([sys.executable, '-W', 'error', '-B',
            str(folder / 'generate_public_acceptance.py')], capture_output=True, text=True)
        label = name + ':' + '/'.join(path)
        rejected = result.returncode != 0 and not (folder / 'PUBLIC-LATEST-ACCEPTANCE.json').exists()
        runs.append({'name': label, 'mutated_value': value, 'returncode': result.returncode,
            'rejected': rejected, 'stdout': result.stdout, 'stderr': result.stderr})
        check('reject_individual_' + label, rejected)
result = {'reviewed_head': head, 'checks': checks, 'passed': sum(item['passed'] for item in checks),
    'total': len(checks), 'individual_controls': len(runs), 'canonical_manager_map_sha256': canonical_digest,
    'runs': runs}
(output / 'closure-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': result['passed'], 'total': result['total'],
    'individual_controls': len(runs), 'failed': [item['name'] for item in checks if not item['passed']]}))
raise SystemExit(0 if all(item['passed'] for item in checks) else 1)
