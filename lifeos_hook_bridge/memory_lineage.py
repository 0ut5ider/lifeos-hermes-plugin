# ABOUTME: Reads durable compression lineage from the selected private Hermes session database.
# ABOUTME: Uses native continuation predicates and verifies the current author and destination.
import os
from pathlib import Path
import sqlite3
import stat

from .memory_access import MemoryUnavailable


def _private(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise MemoryUnavailable('Compression recovery needs a private owner session database')
    return info


def _matches(row, context):
    if context.transport == 'terminal':
        return row['source'] in ('cli', 'tui')
    destination = row['chat_id'] or ''
    if row['thread_id']:
        destination += '/' + row['thread_id']
    return (row['source'] == context.transport and row['user_id'] == context.author
            and destination == context.destination and row['chat_type'] in ('dm', 'private'))


def compression_parent(profile, context):
    path = Path(profile).absolute() / 'state.db'
    try:
        if path.parent.resolve() != path.parent:
            raise MemoryUnavailable('Compression recovery changes its session database path')
        before = _private(path)
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = path.with_name(path.name + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                _private(sidecar)
        from hermes_state_common import _non_continuation_child_sql
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('BEGIN')
            child = connection.execute('SELECT * FROM sessions WHERE id=?', (context.session_id,)).fetchone()
            if child is None or not child['parent_session_id']:
                raise MemoryUnavailable('Compression recovery has no durable parent')
            parent_id = child['parent_session_id']
            parent = connection.execute('SELECT * FROM sessions WHERE id=?', (parent_id,)).fetchone()
            if (parent is None or parent['end_reason'] != 'compression' or parent['ended_at'] is None
                    or child['ended_at'] is not None or child['end_reason'] is not None):
                raise MemoryUnavailable('Compression recovery needs a committed live continuation')
            children = connection.execute('SELECT id FROM sessions WHERE parent_session_id=? AND ended_at IS NULL'
                + _non_continuation_child_sql() + ' LIMIT 2', (parent_id,) * 4).fetchall()
            if len(children) != 1 or children[0]['id'] != context.session_id:
                raise MemoryUnavailable('Compression recovery cannot resolve an unambiguous continuation')
            if not _matches(parent, context) or not _matches(child, context):
                raise MemoryUnavailable('Compression recovery changes its native author or destination')
        finally:
            connection.close()
        after = _private(path)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise MemoryUnavailable('The session database changed during compression recovery')
        return parent_id
    except (OSError, sqlite3.Error, ImportError, KeyError, IndexError, TypeError) as error:
        raise MemoryUnavailable('Compression recovery cannot verify its session database') from error
