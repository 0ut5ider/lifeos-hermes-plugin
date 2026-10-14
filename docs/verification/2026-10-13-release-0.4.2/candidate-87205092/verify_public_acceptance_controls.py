# ABOUTME: Tests rejection of stale and incomplete public installation receipts.
# ABOUTME: Mutates only temporary copies and preserves the prepared acceptance checkpoint.
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

source = Path(__file__).resolve().parent
cases = [
    ('current', None, None, None),
    ('wrong-rc3-commit', 'public-rc3-baseline.json', ['active_identity', 'commit'], '0' * 40),
    ('wrong-fresh-reference', 'public-fresh-owner-turn-verification.json', ['reference', 'id'], '0' * 32),
    ('unapplied-conversation', 'public-conversation-update-applied.json', ['operation_state'], 'applying'),
    ('wrong-conversation-operation', 'public-conversation-update-applied.json', ['operation'], '0' * 32),
    ('changed-update-model', 'public-lifeos-update-applied.json', ['model_selection_sha256'], '0' * 64),
    ('missing-memory-proof', 'public-plugin-update-memory-preservation.json', ['matched_content'], False),
    ('wrong-manager-file-digest', 'public-default-github-manager-install.json', ['files', 'release_worker.py', 'sha256'], '0' * 64),
    ('mixed-fresh-guest', 'public-latest-fresh-preparation.json', ['guest'], 109),
    ('wrong-daily-package-identity', 'final-server-identities.json', ['servers', 1, 'active_identity', 'commit'], '0' * 40),
    ('wrong-published-package-digest', 'stable-publication.json', ['asset_digests', '0.4.2-87205092.tgz'], '0' * 64),
    ('wrong-stock-hermes-base', 'public-default-github-manager-install.json', ['hermes_base'], '0' * 40),
    ('wrong-owner-model-selection', 'public-fresh-ownership-activation.json', ['model_selection_sha256'], '0' * 64),
    ('empty-public-service-map', 'public-lifeos-update-applied.json', ['services'], {}),
]
results = []
for name, receipt, keys, value in cases:
    with tempfile.TemporaryDirectory(prefix='lifeos-public-controls-') as temporary:
        target = Path(temporary) / 'evidence'
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('PUBLIC-LATEST-ACCEPTANCE.json', '__pycache__'))
        if receipt:
            path = target / receipt
            data = json.loads(path.read_bytes())
            current = data
            for key in keys[:-1]:
                current = current[key]
            current[keys[-1]] = value
            path.write_text(json.dumps(data))
        run = subprocess.run([sys.executable, '-B', str(target / 'verify_public_acceptance.py')], capture_output=True)
        accepted = run.returncode == 0
        if name == 'current':
            assert (target / 'PUBLIC-LATEST-ACCEPTANCE.json').read_bytes() == (source / 'PUBLIC-LATEST-ACCEPTANCE.json').read_bytes()
        results.append({'case': name, 'accepted': accepted, 'expected': name == 'current',
            'exit_code': run.returncode, 'actual_receipts_used': True, 'test_copy_only': True})
(source / 'public-acceptance-controls.json').write_text(json.dumps(results, indent=2) + '\n')
assert all(row['accepted'] == row['expected'] for row in results), results
print(json.dumps({'status': 'PASS', 'cases': len(results)}))
