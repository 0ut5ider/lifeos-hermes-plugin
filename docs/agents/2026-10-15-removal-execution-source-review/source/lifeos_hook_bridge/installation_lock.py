# ABOUTME: Serializes installation admission and detached program transactions for one profile.
# ABOUTME: Holds a private operating-system lock that process exit releases automatically.

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
import threading


class InstallationBusy(RuntimeError):
    pass


class _InstallationLease:
    def __init__(self, profile, descriptor):
        self.profile = profile
        self.descriptor = descriptor
        self.owner = (os.getpid(), threading.get_ident())
        self.active = True
        info = os.fstat(descriptor)
        self.identity = (info.st_dev, info.st_ino)
        self.profile_identity = (profile.stat().st_dev, profile.stat().st_ino)

    def check(self, profile):
        if not self.active:
            raise RuntimeError('The installation lease has expired')
        if (os.getpid(), threading.get_ident()) != self.owner:
            raise RuntimeError('Only the installation lease owner can borrow the lock')
        if profile != self.profile:
            raise RuntimeError('The installation lease belongs to another profile')
        try:
            descriptor = os.fstat(self.descriptor)
            current_profile = profile.stat()
            state = profile / '.lifeos-installation'
            directory = state.lstat()
            current = (state / 'lock').lstat()
        except OSError as error:
            raise RuntimeError('The installation lease physical identity is unavailable') from error
        if (profile.resolve() != profile or (current_profile.st_dev, current_profile.st_ino) != self.profile_identity
                or (descriptor.st_dev, descriptor.st_ino) != self.identity
                or (current.st_dev, current.st_ino) != self.identity):
            raise RuntimeError('The installation lease physical identity changes')
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid() or directory.st_mode & 0o077
                or current_profile.st_uid != os.getuid() or current_profile.st_mode & 0o022
                or not stat.S_ISREG(current.st_mode) or current.st_uid != os.getuid() or current.st_mode & 0o077):
            raise RuntimeError('The installation lease needs private owner permissions')


@contextmanager
def installation_lock(profile: Path, *, wait: bool = False, lease=None):
    profile = Path(profile).absolute()
    if lease is not None:
        if not isinstance(lease, _InstallationLease):
            raise RuntimeError('The installation operation requires an issued owner lease')
        lease.check(profile)
        yield lease
        lease.check(profile)
        return
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
            raise InstallationBusy('Another installation operation is running') from error
        issued = _InstallationLease(profile, descriptor)
        try:
            yield issued
        finally:
            issued.active = False
    finally:
        os.close(descriptor)
