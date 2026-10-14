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
cases = [
    ('completed-inputs', None, None),
    ('failed-integration', 'integration-archive-bound-a1abb579.json', lambda row: row.update(exit_code=1)),
    ('stale-restore-commit', 'bound-whole-guest-recovery.json', lambda row: row.update(program_commit='0' * 40)),
    ('missing-atlas-case', 'bound-whole-guest-recovery.json', lambda row: row['cases'].pop()),
    ('changed-runtime-count', 'bound-whole-guest-artifact-coverage.json', lambda row: row.update(artifacts=row['artifacts'] - 1)),
    ('changed-operation', 'bound-whole-guest-program-coverage.json', lambda row: row.update(operation='0' * 32)),
    ('no-owner-admission', 'collection-interruption-exit.json', lambda row: row.update(authenticated_owner_verified=False)),
    ('changed-native-inputs', 'unchanged-native-inputs.json', lambda row: next(iter(row['inputs'].values())).update(program_identity_equal=False)),
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
        assert rejected == bool(mutation), name
        assert (root / 'RELEASE-CERTIFICATE.json').exists() == (mutation is None), name
        results.append({'case': name, 'result': 'refused' if rejected else 'completed original inputs accepted'})
report = {'status': 'PASS', 'controls': results, 'temporary_evidence_mutations_only': True,
          'guest_completion_receipt_constructed': False, 'published_asset_changed': False}
(source / 'certificate-negative-controls.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
