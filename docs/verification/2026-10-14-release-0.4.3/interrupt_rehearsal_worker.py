# ABOUTME: Runs the admitted frozen entrypoint and exits at the published-program boundary.
# ABOUTME: Preserves entrypoint policy and file masks while retaining an actual process-exit control.
import importlib
import inspect
import os
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
job = Path(sys.argv[1]).absolute()
namespace = types.ModuleType('observed_release_worker')
namespace.__path__ = [str(job / 'worker')]
sys.modules[namespace.__name__] = namespace
worker = importlib.import_module(namespace.__name__ + '.release_worker')
lines, first = inspect.getsourcelines(worker._execute)
target = first + next(index for index, line in enumerate(lines)
    if line.strip() == "checkpoint('programs-published')")


def trace(frame, event, value):
    if frame.f_code is worker._execute.__code__ and event == 'line' and frame.f_lineno == target:
        os._exit(73)
    return trace


sys.argv = ['release_worker.py', str(job), '--action', 'apply']
sys.settrace(trace)
raise SystemExit(worker.main())
