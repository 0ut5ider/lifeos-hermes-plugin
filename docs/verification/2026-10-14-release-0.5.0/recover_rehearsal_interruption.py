# ABOUTME: Recovers a synthetic interrupted native update with its authenticated owner grant.
# ABOUTME: Uses the actual frozen admission path and verifies the restored selected programs.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

os.umask(0o077)
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
stage = home / 'releases/qualification-0.5.0'
environment = json.loads((home / 'deployment/2026-10-14/environment.json').read_bytes())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/1000', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
observed = json.loads((stage / 'observed-worker-started.json').read_bytes())
assert observed['exit_status'] == 73 and observed['authenticated_owner_verified']
job = profile / '.lifeos-releases' / observed['operation']
request = json.loads((job / 'request.json').read_bytes())
authority = json.loads((stage / 'private-recovery-authority.json').read_bytes())
assert authority['operation'] == job.name and authority['expires_at'] > time.time()
sys.path.insert(0, request['runtime']['source'])
namespace = types.ModuleType('observed_release_worker')
namespace.__path__ = [str(job / 'worker')]
sys.modules[namespace.__name__] = namespace
worker = importlib.import_module(namespace.__name__ + '.release_worker')
report = {'status': 'FAIL', 'operation': job.name, 'test_fixture_only': True, 'production_guest_changed': False}
code = 1
try:
    current = worker.recovery_bridge(job, profile)
    administration = current.memory_administration()
    configuration = administration.MemoryConfiguration(profile / 'lifeos-memory.json')
    configuration.check_owner(configuration.load(), authority['account'])
    commands = importlib.import_module(namespace.__name__ + '.cli')
    result = commands.launch(profile, job.name, 'recover', authorization=Path(authority['authorization']))
    deadline = time.monotonic() + 900
    while True:
        state = json.loads((job / 'status.json').read_bytes())['state']
        if state == 'rolled_back': break
        assert state not in {'failed', 'recovery_required'}
        assert time.monotonic() < deadline
        time.sleep(1)
    python = home / '.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
    with (stage / 'recovered-verification.stdout').open('w') as out, (stage / 'recovered-verification.stderr').open('w') as err:
        verified = subprocess.run([str(python), '-B', str(stage / 'verify_rehearsal.py'), '0.3.1', 'restored'], stdout=out, stderr=err, timeout=180)
    assert verified.returncode == 0
    report.update(status='PASS', state='rolled_back', authenticated_owner_grant=True,
        prior_and_post_update_synthetic_memory_preserved=True, selected_programs_verified=True)
    code = 0
finally:
    (stage / 'recovered-action.json').write_text(json.dumps(report, indent=2) + '\n')
    (stage / 'recovered-action.done').write_text(str(code) + '\n')
