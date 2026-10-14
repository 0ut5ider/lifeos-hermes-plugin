# ABOUTME: Replays completed qualification inputs and verifies refusal of altered evidence.
# ABOUTME: Uses private temporary copies and never exports a constructed guest completion receipt.
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import tempfile

source = Path(__file__).resolve().parent


def change_restore_guest(rows):
    next(row for row in rows if row['label'] == 'restore')['command'][2] = '253'


def change_restore_archive(rows):
    next(row for row in rows if row['label'] == 'restore')['command'][3] = 'PBS-01:backup/ct/111/2026-10-13T00:00:00Z'


cases = [
    ('completed-inputs', None, None),
    ('failed-integration', 'integration-archive-bound-a1abb579.json', lambda row: row.update(exit_code=1)),
    ('stale-restore-commit', 'bound-whole-guest-recovery.json', lambda row: row.update(program_commit='0' * 40)),
    ('missing-atlas-case', 'bound-whole-guest-recovery.json', lambda row: row['cases'].pop()),
    ('changed-runtime-count', 'bound-whole-guest-artifact-coverage.json', lambda row: row.update(artifacts=row['artifacts'] - 1)),
    ('changed-operation', 'bound-whole-guest-program-coverage.json', lambda row: row.update(operation='0' * 32)),
    ('no-owner-admission', 'collection-interruption-exit.json', lambda row: row.update(authenticated_owner_verified=False)),
    ('changed-native-inputs', 'unchanged-native-inputs.json', lambda row: next(iter(row['inputs'].values())).update(program_identity_equal=False)),
    ('empty-service-details', 'verify-applied.json', lambda row: row.update(services={key: {} for key in row['services']})),
    ('wrong-rollback-identity', 'verify-restored.json', lambda row: row['active'].update(commit='0' * 40, package_sha256='0' * 64)),
    ('mixed-restore-guest', 'bound-whole-guest-program-coverage.json', lambda row: row.update(source_guest=102, restored_guest=253)),
    ('empty-native-inputs', 'unchanged-native-inputs.json', lambda row: row.update(inputs={})),
    ('interrupted-programs-still-applied', 'daily-layout-operation-states.json', lambda row: next(item for item in row['operations'] if item['operation'] == 'bb646e0d665d4e3f9483aa32671247e5').update(program_state='applied')),
    ('later-edit-was-not-refused', 'bound-whole-guest-recovery.json', lambda row: next(item for item in row['cases'] if item['case'] == 'later-edit').update(later_edit_refused=False)),
    ('mixed-restore-command-guest', 'bound-whole-guest-operations.json', change_restore_guest),
    ('mixed-restore-command-archive', 'bound-whole-guest-operations.json', change_restore_archive),
]
results = []
with tempfile.TemporaryDirectory(prefix='lifeos-043-certificate-controls-') as temporary:
    for name, file, mutation in cases:
        root = Path(temporary) / name / '2026-10-14-release-0.4.3'
        root.mkdir(parents=True)
        for path in source.iterdir():
            if path.is_file() and path.name != 'RELEASE-CERTIFICATE.json':
                shutil.copyfile(path, root / path.name)
        prior = root.parent / '2026-10-13-release-0.4.2/candidate-87205092'
        prior.mkdir(parents=True)
        shutil.copyfile(source.parent / '2026-10-13-release-0.4.2/candidate-87205092/RELEASE-CERTIFICATE.json', prior / 'RELEASE-CERTIFICATE.json')
        if file:
            path = root / file
            receipt = json.loads(path.read_bytes())
            mutation(receipt)
            path.write_text(json.dumps(receipt))
        rejected = False
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                runpy.run_path(str(root / 'certify_release.py'), run_name='__main__')
            except AssertionError:
                rejected = True
        correct = rejected == bool(mutation) and (root / 'RELEASE-CERTIFICATE.json').exists() == (mutation is None)
        results.append({'case': name, 'expected_result_verified': correct,
                        'result': 'refused' if rejected else 'accepted'})
report = {'status': 'PASS' if all(row['expected_result_verified'] for row in results) else 'FAIL',
          'controls': results, 'temporary_evidence_mutations_only': True,
          'guest_completion_receipt_constructed': False, 'published_asset_changed': False}
(source / 'certificate-negative-controls.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
assert report['status'] == 'PASS', 'The certifier accepts altered or incomplete qualification evidence'
