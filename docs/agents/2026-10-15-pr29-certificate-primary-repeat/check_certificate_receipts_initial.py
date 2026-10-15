# ABOUTME: Checks the saved release certificate against local qualification receipts.
# ABOUTME: Regenerates the certificate in memory and saves review results only.
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FOLDER = ROOT / 'docs/verification/2026-10-15-memory-portability'
CERTIFICATE = ROOT / 'docs/verification/2026-10-15-release-0.6.0/RELEASE-CERTIFICATE.json'
EXPECTED_CERTIFICATE = 'e53fa1a02d52637fd9678d6978900c10d3003bb2059c78c689078bc0de3db770'
BUILD = Path('/home/outsider/.cache/lifeos-memory-portability-20261015/removal-workflow-packages/0.6.0-c86b5887-build.json')
DASHBOARD = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')
WORKFLOW = 'ab99723289884679b706440c7005fa5c'
ARCHIVE = 'PBS-01:backup/ct/110/2026-10-15T21:26:10Z'
FILES = {'MEMORY.md': {'bytes': 780, 'sha256': '85947afbbd323e608d2818f769097b51badbcb797f09fd04fb0392be99745435'},
         'USER.md': {'bytes': 267, 'sha256': '7d9e0df1fd2bcba72f3bdcb2b73782bcf15318ed79c923c2e999014710f0c2db'}}
SHA_FILES = {name: value['sha256'] for name, value in FILES.items()}
checks = {}
raw = {}


def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def check(name, condition):
    checks[name] = bool(condition)


def read(name):
    return json.loads((FOLDER / name).read_bytes())


certificate = json.loads(CERTIFICATE.read_bytes())
raw['certificate_sha256'] = digest(CERTIFICATE)
check('certificate_sha256', raw['certificate_sha256'] == EXPECTED_CERTIFICATE)
receipt_hashes = {name: digest(FOLDER / name) for name in certificate['qualification_receipt_sha256']}
raw['receipt_sha256'] = receipt_hashes
check('receipt_count_41', len(receipt_hashes) == 41)
check('receipt_hashes_match', receipt_hashes == certificate['qualification_receipt_sha256'])
closure = certificate['verification_operator_review']
source_hashes = {name: digest(ROOT / name) for name in closure['source_sha256']}
raw['operator_source_sha256'] = source_hashes
check('operator_count_9', len(source_hashes) == 9)
check('operator_hashes_match', source_hashes == closure['source_sha256'])
report = ROOT / closure['report']
raw['closure_report_sha256'] = digest(report)
check('closure_report_hash_and_clear', digest(report) == closure['report_sha256'] and
      'Review status: CLEAR' in report.read_text().splitlines() and closure['status'] == 'CLEAR')

spec = importlib.util.spec_from_file_location('certificate_receipt_review_operator', FOLDER / 'certify_release.py')
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)
generated = operator.certify(FOLDER, BUILD, DASHBOARD)
check('in_memory_certificate_equal', generated == certificate)
check('production_qualified', certificate['production_qualified'] is True)
check('later_gates_explicit', certificate['daily_promotion_verified'] is False and
      certificate['development_promotion_verified'] is False and
      certificate['public_default_url_replay_for_060'] == 'Pending public publication')

cold = read('cold-restore-verification.json')
native = read('cold-restored-native-verification.json')
auth = read('cold-restored-authentication.json')
rollback = read('cold-restored-final-rollback.json')
version = read('cold-restored-version.json')
operations = read('cold-restore-operations.json')
by_label = {row['label']: row for row in operations}
check('cold_source_restore_offline', cold['status'] == 'PASS' and cold['source_guest'] == 110 and
      cold['restored_guest'] == 111 and cold['archive'] == ARCHIVE and cold['archive_protected'] is True and
      cold['network_disconnected'] is True and cold['restored_guest_stopped'] is True and
      cold['production_guest_changed'] is False and cold['all_original_guest_states_preserved'] is True)
check('cold_process_success', (FOLDER / 'cold-restore-process.done').read_text().strip() == '0')
check('cold_native_exact_receipt', cold['native_consistency'] == native)
check('cold_native_actual_proof', native['workflow'] == WORKFLOW and native['status'] == 'PASS' and
      all(native[name] is True for name in ('retained_bootstrap_help_verified', 'owner_authenticated',
          'native_consistency_signature_verified', 'program_targets_verified', 'stock_runtime_verified',
          'fresh_stock_constructor_verified', 'builtin_files_unchanged')) and
      native['builtin_files'] == SHA_FILES and bool(native['native_signature']))
check('cold_auth_exact_receipt', cold['retained_helper_authentication'] == auth)
check('cold_auth_actual_rollback', auth['status'] == 'PASS' and auth['workflow'] == WORKFLOW and
      auth['action'] == 'rollback' and auth['exit_code'] == 0 and auth['wrong_password'] is False and
      all(auth[name] is True for name in ('actual_terminal', 'username_prompt', 'password_prompt',
          'password_echo_disabled', 'admitted', 'builtin_memory_unchanged')) and
      auth['before_sha256'] == auth['after_sha256'] == SHA_FILES)
check('cold_rollback_terminal', rollback['workflow'] == WORKFLOW and
      rollback['workflow_status']['state'] == rollback['publication_status']['state'] ==
      rollback['workflow_receipt']['state'] == 'rolled_back' and
      set(rollback['active_software_present']) == {'lifeos', 'lifeos-hook-bridge', 'lifeos-release-manager'} and
      all(rollback['active_software_present'].values()) and rollback['removal_marker_present'] is False)
check('cold_builtin_bytes_hashes', cold['builtin_files'] == rollback['builtin_files'] == FILES)
check('cold_version_identity', version['active'] == cold['active_identity'] and
      version['active']['version'] == '0.6.0' and
      version['active']['commit'] == 'c86b5887b899ca779afbb217c33843e1ee12c381' and
      version['active']['package_sha256'] == certificate['archive_sha256'] and
      certificate['archive_bytes'] == 288167820)
check('cold_operations_bound', digest(FOLDER / 'cold-restore-operations.json') == cold['operations_sha256'])
check('cold_operations_success', all(row['exit_code'] == 0 for row in operations))
check('cold_backup_target', by_label['backup-source']['command'][:2] == ['vzdump', '110'] and
      by_label['backup-source']['command'][2:4] == ['--storage', 'PBS-01'])
check('cold_restore_target', by_label['restore']['command'][:4] == ['pct', 'restore', '111', ARCHIVE])
check('cold_disconnect_target', by_label['disconnect']['command'][:5] == ['pct', 'set', '111', '--delete', 'net0'])
required = ['backup-source', 'restore', 'disconnect', 'boot-offline', 'restored-native-verification',
            'restored-authentication', 'restored-version', 'shutdown-restore']
labels = [row['label'] for row in operations]
check('cold_operation_order', [labels.index(label) for label in required] ==
      sorted(labels.index(label) for label in required))
check('cold_verifier_target', by_label['restored-native-verification']['command'][:3] == ['pct', 'exec', '111'] and
      by_label['restored-native-verification']['command'][-1].endswith('/verify_restored_removal.py'))
auth_command = by_label['restored-authentication']['command']
check('cold_auth_command_target', auth_command[:3] == ['pct', 'exec', '111'] and
      any(arg.endswith('/observe_guest_recovery_auth.py') for arg in auth_command) and
      auth_command[-4:-2] == [WORKFLOW, 'rollback'])
check('cold_version_shutdown_target', by_label['restored-version']['command'][:3] == ['pct', 'exec', '111'] and
      by_label['restored-version']['command'][-1] == 'lifeos-version' and
      by_label['shutdown-restore']['command'][:3] == ['pct', 'shutdown', '111'])
raw['cold_receipts_sha256'] = {name: digest(FOLDER / name) for name in (
    'cold-restore-verification.json', 'cold-restore-operations.json', 'cold-restore-process.done',
    'cold-restored-native-verification.json', 'cold-restored-authentication.json',
    'cold-restored-final-rollback.json', 'cold-restored-version.json')}
raw['cold_states'] = {'source_guest': cold['source_guest'], 'restored_guest': cold['restored_guest'],
    'archive': cold['archive'], 'workflow': cold['workflow'], 'workflow_state': rollback['workflow_status']['state'],
    'publication_state': rollback['publication_status']['state'], 'operation_count': len(operations),
    'operation_labels': labels, 'builtin_files': FILES}
raw['operational_cold_files'] = sorted(path.name for path in FOLDER.glob('cold*'))
check('no_synthetic_cold_receipt_names', not any('synthetic' in name or 'fixture' in name for name in raw['operational_cold_files']))
raw['checks'] = checks
raw['status'] = 'CLEAR' if all(checks.values()) else 'FINDINGS'
raw['scope'] = 'Local evidence only. No remote operation or full test suite repeated.'
with (OUT / 'receipt-checks.json').open('x') as stream:
    json.dump(raw, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': raw['status'], 'checks': len(checks), 'failed': [name for name, ok in checks.items() if not ok],
                  'certificate_sha256': raw['certificate_sha256'], 'receipts': len(receipt_hashes), 'operators': len(source_hashes),
                  'cold_states': raw['cold_states']}))
raise SystemExit(0 if all(checks.values()) else 1)
