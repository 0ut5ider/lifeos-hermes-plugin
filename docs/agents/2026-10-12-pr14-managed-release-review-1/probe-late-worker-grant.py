# ABOUTME: Runs a stale apply worker against a later synthetic recovery admission.
# ABOUTME: Checks whether rejected execution deletes the newer private grant artifact.
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
PACKAGE = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/packages/0.4.0-dev.1-3a072309')
namespace = types.ModuleType('frozen_review_manager')
namespace.__path__ = [str(PACKAGE / 'optional/lifeos_release_manager')]
sys.modules[namespace.__name__] = namespace
worker = importlib.import_module(namespace.__name__ + '.release_worker')
cli = importlib.import_module(namespace.__name__ + '.cli')
operations = importlib.import_module(namespace.__name__ + '.release_operation')
programs = importlib.import_module(namespace.__name__ + '.release_programs')
with tempfile.TemporaryDirectory() as temporary:
    profile = Path(temporary)
    job = profile / '.lifeos-releases' / ('a' * 32)
    job.mkdir(parents=True, mode=0o700)
    shutil.copytree(PACKAGE / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    grants = profile / '.lifeos-memory-admin'
    grants.mkdir(mode=0o700)
    grant = grants / ('b' * 32 + '.json')
    programs.publish(grant, b'Synthetic later recovery grant; contains no credential')
    request = {'identifier': job.name, 'profile': str(profile), 'runtime': {'source': str(PACKAGE / 'hermes')}, 'memory_authorization': str(grant)}
    programs.publish(job / 'request.json', json.dumps(request).encode())
    cli.write_state(job, 'ready')
    operations.seal_plan(job, request, {'fresh': False, 'native_mount_required': True, 'services': None})
    operations.write_admission(job, request, 'recover')
    cli.write_state(job, 'queued-recover')
    print('newer recovery grant exists before stale worker:', grant.exists(), flush=True)
    child = os.fork()
    if child == 0:
        try:
            worker.execute(job, 'apply')
        except Exception as error:
            print('stale apply execution:', type(error).__name__ + ': ' + str(error), flush=True)
            os._exit(73)
        os._exit(74)
    _, result = os.waitpid(child, 0)
    print('stale worker process exit:', os.waitstatus_to_exitcode(result))
    print('newer recovery grant exists after rejected stale worker:', grant.exists())
    print('operation state:', cli.read_private(job / 'status.json')['state'])
