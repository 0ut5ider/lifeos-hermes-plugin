# ABOUTME: Serializes core-file publication and recovery with installed program transactions.
# ABOUTME: Allows nested recovery to borrow only the current thread's active physical-profile lease.
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .installation_lock import installation_lock, InstallationBusy
from . import program_lock

_current = ContextVar('core_file_installation_lease', default=None)


@contextmanager
def core_file_lease(profile):
    from .memory_access import MemoryUnavailable
    profile = Path(profile).resolve()
    current = _current.get()
    if current is not None:
        current.check(profile)
        yield
        current.check(profile)
        return
    try:
        with installation_lock(profile) as issued, program_lock.exclusive(profile, timeout=0):
            token = _current.set(issued)
            try:
                yield
            finally:
                _current.reset(token)
    except (InstallationBusy, program_lock.ProgramBusy) as error:
        raise MemoryUnavailable('Core files wait for current turns and installation operations') from error


@contextmanager
def core_file_read_lease(memory):
    from .memory_access import MemoryUnavailable
    # Pending core publication recovery needs an exclusive lease before this read holds a shared lease.
    with memory._transaction():
        pass
    descriptor = program_lock.shared(memory.physical_profile)
    if descriptor is None:
        raise MemoryUnavailable('Core files wait for the installed program transaction')
    try:
        yield
    finally:
        program_lock.release(descriptor)
