# ABOUTME: Runs memory ownership operations outside the profile services that they restart.
# ABOUTME: Leaves a private interrupted status and never exports memory content or credentials to the service log.
import argparse
from pathlib import Path
import sys
import types

sys.dont_write_bytecode=True

if not __package__:
    package=types.ModuleType('lifeos_memory_workflow_manager')
    package.__path__=[str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__]=package
    __package__=package.__name__

from .memory_workflow import execute, _job, _state


def main():
    parser=argparse.ArgumentParser(description='Run an authenticated reviewed memory workflow')
    parser.add_argument('job',type=Path)
    parser.add_argument('action',choices=('prepare','apply','recover','rollback'))
    args=parser.parse_args()
    job=args.job.absolute()
    try:
        if job.parent.name!='.lifeos-portability':raise ValueError('Use a fixed private memory workflow')
        execute(job.parent.parent,job.name,args.action)
    except BaseException:
        try:
            admitted,_=_job(job.parent.parent,job.name)
            _state(admitted,'interrupted')
        except (OSError,ValueError,RuntimeError):pass
        print('The memory workflow stopped. The owner can review its private recovery state.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
