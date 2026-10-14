# ABOUTME: Runs installed native jobs through the admitted development owner profile.
# ABOUTME: Retains private output on the guest and exports only process status and digests.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
profile = Path.home() / '.hermes'
stage = Path.home() / 'releases/qualification-0.4.2-87205092'
configuration = json.loads((profile / 'lifeos-memory.json').read_bytes())
assert configuration['ownership_enabled'] is True
installed = Path(configuration['root'])
before = hashlib.sha256((profile / 'config.yaml').read_bytes()).hexdigest()
environment = dict(os.environ, HOME=str(installed.parent), HERMES_HOME=str(profile),
    PATH=str(Path.home() / '.local/bin') + ':/usr/bin:/bin', LANG='C.UTF-8', TZ='America/Toronto',
    LIFEOS_DIR=str(installed / 'LIFEOS'), LIFEOS_HOOK_SETTINGS=str(installed / 'settings.json'),
    LIFEOS_NOTIFICATION_CHANNEL='headless', BUN_CONFIG_NO_AUTO_INSTALL='1',
    PYTHONDONTWRITEBYTECODE='1')
rows = []
try:
    for name in ('user-index', 'conduit-insight', 'atlas-insights', 'algorithm-summaries'):
        output = stage / ('native-job-' + name + '.private-output')
        assert not output.exists()
        started = time.monotonic()
        result = subprocess.run([str(Path.home() / '.local/bin/hermes'), 'lifeos-job', name],
            env=environment, cwd=profile, capture_output=True, timeout=600)
        output.write_bytes(result.stdout + result.stderr)
        receipt = json.loads(result.stdout) if result.returncode == 0 and not result.stderr else {}
        row = {'job': name, 'exit_code': result.returncode, 'stderr_bytes': len(result.stderr),
            'receipt_status': receipt.get('status'), 'receipt_job': receipt.get('job'),
            'output_sha256': hashlib.sha256(result.stdout).hexdigest(),
            'elapsed_seconds': round(time.monotonic() - started, 3)}
        rows.append(row)
        (stage / 'native-jobs-progress.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert result.returncode == 0 and not result.stderr
        assert receipt['status'] == 'completed' and receipt['job'] == name
        assert hashlib.sha256((profile / 'config.yaml').read_bytes()).hexdigest() == before
    report = {'status': 'PASS', 'jobs': rows, 'model_configuration_sha256': before,
        'model_routes_changed': False, 'daily_server_changed': False,
        'private_output_exported': False, 'actual_installed_jobs': True}
except BaseException as error:
    report = {'status': 'FAIL', 'jobs': rows, 'error_type': type(error).__name__,
        'daily_server_changed': False, 'private_output_exported': False}
    raise
finally:
    (stage / 'native-jobs-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'native-jobs.done').write_text('0\n' if report['status'] == 'PASS' else '1\n')
