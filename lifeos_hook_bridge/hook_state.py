# ABOUTME: Coordinates native post-hook state updates for one session across bridge processes.
# ABOUTME: Uses owner-only advisory locks that the operating system releases after interruption.
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import stat


@contextmanager
def session_state(root: Path, session_id: str):
    directory = root / 'LIFEOS/MEMORY/STATE/hermes-post-locks'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('Post-hook state requires a private owner directory')
    name = hashlib.sha256(session_id.encode()).hexdigest() + '.lock'
    descriptor = os.open(directory / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise RuntimeError('Post-hook state requires a private owner lock')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)
