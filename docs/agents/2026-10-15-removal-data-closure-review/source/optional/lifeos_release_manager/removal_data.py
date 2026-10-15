# ABOUTME: Locks retained native data during software removal without installed memory tools.
# ABOUTME: Reads the existing registry without migrations, content writes, or pending recovery publication.
from contextlib import contextmanager
import os
import sqlite3
import stat
from urllib.parse import quote

from .release_catalog import ReleaseRejected


@contextmanager
def barrier(memory):
    memory._data_boundary()
    database=memory.database.resolve(strict=True)
    user=(memory.root.parent/'.config/LIFEOS/USER').resolve(strict=True)
    if not database.is_relative_to(user):
        raise ReleaseRejected('The retained native registry leaves the reviewed data boundary')
    descriptor=os.open(database,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_mode & 0o077
                or before.st_nlink!=1):
            raise ReleaseRejected('Removal verification requires the existing private native registry')
        with memory.transaction.lock():
            memory._data_boundary()
            if memory.transaction.journal.exists() or memory.transaction.journal.is_symlink():
                raise ReleaseRejected('Recover the pending native memory publication before software removal')
            connection=sqlite3.connect('file:'+quote(str(database),safe='/')+'?mode=rw',uri=True,
                timeout=30,isolation_level=None)
            connection.row_factory=sqlite3.Row
            try:
                connection.execute('BEGIN IMMEDIATE')
                connection.execute('PRAGMA query_only=ON')
                if connection.execute('PRAGMA user_version').fetchone()[0]!=4:
                    raise ReleaseRejected('Removal verification requires the current native registry schema')
                identity=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_nlink)
                if memory.database.resolve()!=database or identity(database.stat())!=identity(before):
                    raise ReleaseRejected('The retained native registry changes its physical identity')
                yield connection
                memory._data_boundary()
                if memory.database.resolve()!=database or identity(database.stat())!=identity(before):
                    raise ReleaseRejected('The retained native registry changes during removal verification')
            finally:
                connection.rollback();connection.close()
    finally:os.close(descriptor)
