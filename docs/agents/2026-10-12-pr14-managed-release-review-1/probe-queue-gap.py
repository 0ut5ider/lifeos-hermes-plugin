# ABOUTME: Reproduces process death after queued admission before launch recording.
# ABOUTME: Uses private synthetic operation files and the actual status and admission functions.
import json
import os
from pathlib import Path
import tempfile
from optional.lifeos_release_manager.cli import status, write_state
from optional.lifeos_release_manager.release_operation import seal_plan, write_admission, worker_running
from optional.lifeos_release_manager.release_programs import publish
from optional.lifeos_release_manager.release_worker import _admit_operation

with tempfile.TemporaryDirectory() as temporary:
    profile = Path(temporary)
    job = profile / '.lifeos-releases' / ('a' * 32)
    job.mkdir(parents=True, mode=0o700)
    request = {'identifier': job.name, 'profile': str(profile), 'version': '0.4.0-dev.1', 'commit': 'b' * 40}
    publish(job / 'request.json', json.dumps(request).encode())
    write_state(job, 'ready')
    seal_plan(job, request, {'fresh': False, 'native_mount_required': False, 'services': None})
    child = os.fork()
    if child == 0:
        write_admission(job, request, 'apply')
        write_state(job, 'queued-apply')
        os._exit(73)
    _, result = os.waitpid(child, 0)
    print('actual process exit:', os.waitstatus_to_exitcode(result))
    print('worker_running:', worker_running(job))
    print('public status:', json.dumps(status(profile, job.name), sort_keys=True))
    try:
        _admit_operation(job, request, 'recover')
    except Exception as error:
        print('recover admission:', type(error).__name__ + ': ' + str(error))
    print('all worker process and launch locks are absent; no worker was spawned')
