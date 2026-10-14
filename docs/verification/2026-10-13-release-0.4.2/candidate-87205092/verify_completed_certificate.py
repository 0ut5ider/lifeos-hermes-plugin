# ABOUTME: Rechecks completed qualification receipts in isolated copies.
# ABOUTME: Verifies refusal of altered recovery evidence without replacing the published certificate.
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

source = Path(__file__).resolve().parent
expected = hashlib.sha256((source / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest()
cases = [
    ('current', None, None, None),
    ('unfinished-cleanup', 'whole-guest-operations.json', 'cleanup', None),
    ('wrong-backup', 'whole-guest-recovery.json', 'archive', 'PBS-01:backup/ct/101/wrong'),
    ('wrong-runtime-map', 'whole-guest-artifact-coverage.json', 'private_map_sha256', '0' * 64),
    ('wrong-target-count', 'whole-guest-program-coverage.json', 'program_targets', 9),
    ('wrong-restored-guest', 'whole-guest-recovery.json', 'restored_guest', 999),
    ('missing-history-case', 'whole-guest-recovery.json', 'cases', None),
]
results = []
for name, receipt, key, value in cases:
    with tempfile.TemporaryDirectory(prefix='lifeos-completed-certificate-') as temporary:
        target = Path(temporary) / 'evidence'
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('RELEASE-CERTIFICATE.json', '__pycache__'))
        if receipt:
            path = target / receipt
            data = json.loads(path.read_bytes())
            if key == 'cleanup':
                data = [row for row in data if row['label'] != 'destroy-disposable']
            elif key == 'cases':
                data[key] = data[key][:-1]
            else:
                data[key] = value
            path.write_text(json.dumps(data))
        run = subprocess.run([sys.executable, '-B', str(target / 'certify_release.py')], capture_output=True)
        accepted = run.returncode == 0
        assert accepted == (name == 'current'), name
        if accepted:
            assert hashlib.sha256((target / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest() == expected
        else:
            assert not (target / 'RELEASE-CERTIFICATE.json').exists()
        results.append({'case': name, 'accepted': accepted, 'expected': name == 'current',
            'exit_code': run.returncode, 'actual_completed_receipts_used': True, 'test_copy_only': True})
assert hashlib.sha256((source / 'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest() == expected
(source / 'final-certificate-binding-controls.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'cases': len(results), 'published_certificate_unchanged': True}))
