# ABOUTME: Measures whether a late same-action failure report changes a successor recovery admission.
# ABOUTME: Uses a real fork and line tracing to pause between execute refusal and main error publication.
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from test_release_operation import ReleaseOperationTests
from optional.lifeos_release_manager.cli import read_private, write_state
from optional.lifeos_release_manager.release_operation import write_admission, validate_admission, operation_lock
from optional.lifeos_release_manager.release_programs import publish
from optional.lifeos_release_manager import release_worker as worker
with tempfile.TemporaryDirectory() as temp:
    profile, job, request = ReleaseOperationTests().recovery_fixture(Path(temp))
    grants = profile / '.lifeos-memory-admin'
    grants.mkdir(mode=0o700)
    first, successor = grants / ('b' * 32 + '.json'), grants / ('c' * 32 + '.json')
    publish(first, b'Synthetic first recovery grant')
    request['memory_authorization'] = str(first)
    publish(job / 'request.json', json.dumps(request).encode())
    write_admission(job, request, 'recover')
    write_state(job, 'queued-recover')
    signal_reader, signal_writer = os.pipe()
    resume_reader, resume_writer = os.pipe()
    lines, start = inspect.getsourcelines(worker.main)
    target = start + next(index for index, line in enumerate(lines) if line.strip() == 'with operation_lock(args.job):')
    child = os.fork()
    if child == 0:
        os.close(signal_reader)
        os.close(resume_writer)
        def trace(frame, event, arg):
            if frame.f_code is worker.main.__code__ and event == 'line' and frame.f_lineno == target:
                sys.settrace(None)
                os.write(signal_writer, b'refused')
                os.read(resume_reader, 1)
            return trace
        sys.argv = ['release_worker.py', str(job), '--action', 'recover']
        sys.settrace(trace)
        code = worker.main()
        os._exit(code)
    os.close(signal_writer)
    os.close(resume_reader)
    try:
        print('first worker reaches late report:', os.read(signal_reader, 16).decode(), flush=True)
        print('first grant cleaned after execution refusal:', not first.exists(), flush=True)
        publish(successor, b'Synthetic successor recovery grant')
        with operation_lock(job, name='launch.lock'):
            worker.admit_operation(job, read_private(job / 'request.json'), 'recover', authorization=successor)
        validate_admission(job, read_private(job / 'request.json'), 'recover')
        print('successor admission before late report:', read_private(job / 'status.json')['state'], flush=True)
        os.write(resume_writer, b'1')
        _, result = os.waitpid(child, 0)
        print('old worker exits:', os.waitstatus_to_exitcode(result))
        print('successor state after late report:', read_private(job / 'status.json')['state'])
        print('successor grant preserved:', successor.exists())
        print('late failure:', read_private(job / 'worker-failure.json')['exception'])
    finally:
        os.close(signal_reader)
        os.close(resume_writer)
