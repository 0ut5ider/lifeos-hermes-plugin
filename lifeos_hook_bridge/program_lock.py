# ABOUTME: Coordinates LifeOS turns with program swaps through one per-profile file lock.
# ABOUTME: Turns hold it shared; update, restore, and recovery workers hold it exclusive.

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
import time

BUSY_MESSAGE = 'LifeOS is updating its installed files. Try again when the update finishes.'


class ProgramBusy(RuntimeError):
    pass


def _open(profile: Path) -> int:
    state = Path(profile) / '.lifeos-installation'
    state.mkdir(mode=0o700, exist_ok=True)
    info = state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('Installation state requires private owner permissions')
    descriptor = os.open(state / 'program.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(descriptor)
        raise RuntimeError('The program lock requires private owner permissions')
    return descriptor


def shared(profile: Path) -> int | None:
    """Return a held shared lock descriptor, or None while a program swap holds the lock."""
    descriptor = _open(profile)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


def release(descriptor: int) -> None:
    os.close(descriptor)


@contextmanager
def exclusive(profile: Path, timeout: float):
    """Hold the program lock after running turns finish; raise ProgramBusy after the timeout."""
    descriptor = _open(profile)
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ProgramBusy('LifeOS turns are still running') from None
                time.sleep(0.2)
        yield
    finally:
        os.close(descriptor)
