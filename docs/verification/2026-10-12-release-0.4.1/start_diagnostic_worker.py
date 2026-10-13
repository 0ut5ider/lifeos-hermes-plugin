# ABOUTME: Starts one admitted development update with private runtime verification instrumentation.
# ABOUTME: Uses the frozen operation admission and the actual owner service manager without changing policy.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

root = Path.home() / 'releases/qualification-20261012-041'
profile = Path.home() / '.hermes'
preparation = json.loads((root / 'diagnostic-preparation.json').read_bytes())
identifier = preparation['preparation']['identifier']
assert identifier == sys.argv[1]
job = profile / '.lifeos-releases' / identifier
request = json.loads((job / 'request.json').read_bytes())
assert request['commit'] == '223cbfc1681f0b4d3a7bad668d40822a9267137e'
sys.path.insert(0, request['runtime']['source'])
namespace = types.ModuleType('diagnostic_worker_admission')
namespace.__path__ = [str(job / 'worker')]
sys.modules[namespace.__name__] = namespace
worker = importlib.import_module(namespace.__name__ + '.release_worker')
os.environ.update(HERMES_HOME=str(profile), XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
with worker.operation_lock(job, name='launch.lock'):
    worker.admit_operation(job, request, 'apply')
    unit = 'lifeos-release-' + identifier
    command = ['systemd-run', '--user', '--collect', '--unit=' + unit,
        '--setenv=HOME=' + str(Path.home()), '--setenv=HERMES_HOME=' + str(profile),
        '--setenv=PATH=' + str(Path.home() / '.local/bin') + ':/usr/local/bin:/usr/bin:/bin',
        '--setenv=PYTHONDONTWRITEBYTECODE=1', request['runtime']['python'], '-B',
        str(root / 'diagnose_installed_verification.py'), str(job)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    worker.publish(job / 'worker-launch.json', json.dumps({'kind':'service', 'unit':unit}).encode())
print(json.dumps({'operation':identifier, 'state':'queued', 'instrumentation_only':True,
    'program_commit':request['commit']}))
