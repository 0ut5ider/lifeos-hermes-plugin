# ABOUTME: Repeats the focused PR30 receipt and source checks without changing release evidence.
# ABOUTME: Measures positive regeneration and individual contradictory evidence controls in temporary directories.
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
args = parser.parse_args()
repo = args.repo.resolve()
args.output.mkdir(parents=True, exist_ok=True)
directory = repo / 'docs/verification/2026-10-15-release-0.6.0'
names = ('public-fixture-reset.json', 'public-fresh-before-application.json',
    'public-manager-source-verification.json', 'public-plugin-scan-confirmation.json',
    'public-fresh-verification.json', 'public-post-model-verification.json',
    'publication.json', 'deployed-checkpoint.json', 'RELEASE-CERTIFICATE.json')
evidence = {name: json.loads((directory / name).read_bytes()) for name in names}
acceptance = json.loads((directory / 'PUBLIC-LATEST-ACCEPTANCE.json').read_bytes())
checks = []


def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})


def git(*arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments])


check('reviewed_head', git('rev-parse', 'HEAD').decode().strip() ==
    '9c886816255bf1226bc3aa606107d48635b281a3')
check('initial_certificate_preserved_from_base', (directory / 'RELEASE-CERTIFICATE.json').read_bytes() ==
    git('show', 'd5386d76:docs/verification/2026-10-15-release-0.6.0/RELEASE-CERTIFICATE.json'))
check('initial_certificate_exact_qualified_hash', hashlib.sha256(
    (directory / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest() ==
    'e53fa1a02d52637fd9678d6978900c10d3003bb2059c78c689078bc0de3db770')
check('no_product_diff', not git('diff', '--name-only', 'd5386d76..9c886816', '--',
    'lifeos_hook_bridge', 'optional', 'VERSION', 'scripts', 'tests').strip())
check('nine_receipt_bindings', len(acceptance['evidence_sha256']) == 9 and
    acceptance['evidence_sha256'] == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
    for name in names})
manager = evidence['public-manager-source-verification.json']
manager_checks = {}
for name, expected in manager['files'].items():
    actual = hashlib.sha256(git('show',
        'c86b5887b899ca779afbb217c33843e1ee12c381:optional/lifeos_release_manager/' + name)).hexdigest()
    manager_checks[name] = {'actual': actual, 'expected': expected, 'matches': actual == expected}
check('all_38_manager_files_match_exact_qualified_program', len(manager_checks) == 38 and
    all(item['matches'] for item in manager_checks.values()))
fresh = evidence['public-fresh-verification.json']
post = evidence['public-post-model-verification.json']
check('public_11_groups_actual_model', fresh['kind'] == 'public' and
    fresh['sealed_program_targets'] == 11 and fresh['actual_model_round_trip'] is True and
    fresh['model_turn_executed'] is True and fresh['tool_names'] == [] and
    fresh['model_session'] == post['model_session'] == '20261015_222532_4ad015')
check('post_model_hash_and_identity_binding', post['prior_model_receipt_sha256'] ==
    hashlib.sha256((directory / 'public-fresh-verification.json').read_bytes()).hexdigest() and
    post['active_identity'] == fresh['active_identity'] and
    post['sealed_programs_verified_after_model'] is True)
check('fresh_model_mapping_binding', fresh['model_mapping_sha256'] ==
    evidence['public-fresh-before-application.json']['model_mapping_sha256'] ==
    'e1eacd900e732f7a8a3348c326fa7d0543d11156cd3c36cdd2a476271ffcbcea' and
    post['selected_model_and_tiers_unchanged_after_model'] is True)
scan = evidence['public-plugin-scan-confirmation.json']
check('scanner_receipt_describes_refusal_and_explicit_confirmation', scan['status'] ==
    'PASS_WITH_EXPLICIT_NATIVE_CONFIRMATION' and scan['initial_http_status'] == 400 and
    scan['native_scan_verdict'] == 'CAUTION' and scan['initial_installation_refused'] is True and
    scan['target_was_empty_before_confirmation'] is True and scan['scanner_disabled'] is False and
    scan['successful_http_response_retained'] is False)
check('scanner_reason_matches_actual_exact_cgroup_read', b"Path('/proc/self/cgroup').read_text()" in
    git('show', 'c86b5887:optional/lifeos_release_manager/removal_consumers.py'))
deployment = evidence['deployed-checkpoint.json']
check('actual_deployment_receipt_keeps_both_servers_on_050', deployment['status'] == 'PASS' and
    all(deployment[name]['version'] == '0.5.0' and deployment[name]['verification'] == 'verified' and
    deployment[name]['modified_files'] == [] for name in ('development', 'daily')) and
    deployment['release_work_changed_development'] is False and
    deployment['release_work_changed_daily'] is False)
publication = evidence['publication.json']
check('actual_publication_receipt_has_exact_initial_assets', publication['status'] == 'PASS' and
    publication['tag'] == 'v0.6.0' and publication['previous_assets_unchanged'] == 56 and
    publication['initial_assets']['v0.6.0/0.6.0-c86b5887.tgz']['digest'] ==
    'sha256:' + acceptance['package_sha256'] and
    publication['initial_assets']['v0.6.0/RELEASE-CERTIFICATE.json']['digest'] ==
    'sha256:e53fa1a02d52637fd9678d6978900c10d3003bb2059c78c689078bc0de3db770')


def regenerate(label, changes=None):
    with tempfile.TemporaryDirectory(prefix='pr30-public-acceptance-') as location:
        folder = Path(location)
        shutil.copy2(directory / 'generate_public_acceptance.py', folder)
        for name in names:
            shutil.copy2(directory / name, folder)
        if changes:
            for name, mutate in changes.items():
                value = copy.deepcopy(evidence[name])
                mutate(value)
                (folder / name).write_text(json.dumps(value, indent=2) + '\n')
        result = subprocess.run([sys.executable, '-W', 'error', '-B',
            str(folder / 'generate_public_acceptance.py')], capture_output=True, text=True)
        generated_path = folder / 'PUBLIC-LATEST-ACCEPTANCE.json'
        generated = json.loads(generated_path.read_bytes()) if generated_path.exists() else None
        return {'label': label, 'returncode': result.returncode, 'stdout': result.stdout,
            'stderr': result.stderr, 'generated_receipt': generated}


runs = [regenerate('positive_unchanged_receipts')]
check('positive_regeneration_exact', runs[0]['returncode'] == 0 and
    runs[0]['generated_receipt'] == acceptance and runs[0]['stderr'] == '')
controls = [
    ('scanner_confirmation_failed', {'public-plugin-scan-confirmation.json': lambda value:
        value.update(status='FAIL', target_was_empty_before_confirmation=False, scanner_disabled=True)}),
    ('deployment_changed', {'deployed-checkpoint.json': lambda value:
        value.update(status='FAIL', release_work_changed_daily=True, personal_data_imported_or_reset=True)}),
    ('public_release_wrong_identity', {'publication.json': lambda value:
        value.update(status='FAIL', tag='v0.5.0', program_commit='0' * 40, initial_assets={})}),
    ('manager_wrong_source', {'public-manager-source-verification.json': lambda value:
        value.update(source='https://example.invalid/private-catalog#pinned-ref')}),
    ('manager_wrong_file_hash', {'public-manager-source-verification.json': lambda value:
        value['files'].update({'plugin.yaml': '0' * 64})}),
]
for label, changes in controls:
    run = regenerate(label, changes)
    runs.append(run)
    check('reject_' + label, run['returncode'] != 0 and run['generated_receipt'] is None,
        {'measured_returncode': run['returncode'], 'generated_status':
            run['generated_receipt'].get('status') if run['generated_receipt'] else None})
result = {'reviewed_head': git('rev-parse', 'HEAD').decode().strip(),
    'checks': checks, 'passed': sum(item['passed'] for item in checks),
    'total': len(checks), 'manager_file_checks': manager_checks, 'runs': runs}
(args.output / 'review-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': result['passed'], 'total': result['total'],
    'failed_checks': [item['name'] for item in checks if not item['passed']]}))
