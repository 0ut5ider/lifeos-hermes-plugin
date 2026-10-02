# ABOUTME: Serializes installation admission and detached program transactions for one profile.
# ABOUTME: Holds a private operating-system lock that process exit releases automatically.

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat


@contextmanager
def installation_lock(profile: Path, *, wait: bool = False):
    profile = Path(profile).absolute()
    info = profile.stat()
    if profile.resolve() != profile or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise RuntimeError('Installation operations require the installed owner profile')
    state = profile / '.lifeos-installation'
    state.mkdir(mode=0o700, exist_ok=True)
    info = state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('Installation state requires private owner permissions')
    descriptor = os.open(state / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise RuntimeError('The installation lock requires private owner permissions')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError as error:
            raise RuntimeError('Another installation operation is running') from error
        yield
    finally:
        os.close(descriptor)
