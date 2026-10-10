# ABOUTME: Runs installed native indexing and model generation against only the synthetic acceptance store.
# ABOUTME: Records actual command outcomes and private cache artifacts while preserving the selected model configuration.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
environment = {'HOME': str(root.parent), 'HERMES_HOME': str(profile),
    'PATH': str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'PYTHONPATH': str(stage / 'package/hermes'), 'LANG': 'C.UTF-8', 'TZ': 'America/Toronto',
    'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(root / 'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'PYTHONDONTWRITEBYTECODE': '1'}
configuration_before = (profile / 'config.yaml').read_bytes()
results = []
for name in ('user-index', 'conduit-insight', 'atlas-insights', 'algorithm-summaries'):
    output = stage / ('installed-graph-job-second-' + name + '.txt')
    assert not output.exists()
    started = time.monotonic()
    result = subprocess.run([str(stage / 'bin/hermes'), 'lifeos-job', name],
        env=environment, cwd=profile, capture_output=True, text=True, timeout=570)
    output.write_text(result.stdout + result.stderr)
    receipt = json.loads(result.stdout) if not result.stderr and result.returncode == 0 else None
    row = {'job': name, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3), 'receipt': receipt}
    results.append(row)
    (stage / 'installed-graph-jobs-second-progress.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'job': name, 'exit_code': result.returncode, 'elapsed_seconds': row['elapsed_seconds'], 'status': None if receipt is None else receipt['status']}), flush=True)
    assert result.returncode == 0 and not result.stderr, 'The actual installed graph job fails: ' + name
    assert receipt['status'] == 'completed' and receipt['job'] == name, receipt
    assert (profile / 'config.yaml').read_bytes() == configuration_before
report = {'status': 'PASS', 'jobs': results, 'synthetic_acceptance_profile_only': True,
    'model_configuration_sha256': hashlib.sha256(configuration_before).hexdigest(),
    'model_routes_changed': False, 'live_profile_changed': False,
    'cache_effects_verified': False, 'wire_efforts_observed': False}
(stage / 'installed-graph-jobs-second-verification.json').write_text(json.dumps(report, indent=2) + '\n')
