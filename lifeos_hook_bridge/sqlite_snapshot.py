# ABOUTME: Serializes committed SQLite state into a verified standalone database image.
# ABOUTME: Normalizes snapshot WAL flags without changing the source connection or journal mode.
from contextlib import closing
import sqlite3


def standalone(connection):
    data = connection.serialize()
    if len(data) < 100 or data[:16] != b'SQLite format 3\x00' or data[18:20] not in (b'\x01\x01', b'\x02\x02'):
        raise sqlite3.DatabaseError('The SQLite snapshot has unsupported format metadata')
    # sqlite3_deserialize requires rollback flags even when the serialized
    # image already includes the committed WAL pages.
    if data[18:20] == b'\x02\x02':
        data = data[:18] + b'\x01\x01' + data[20:]
    with closing(sqlite3.connect(':memory:')) as candidate:
        candidate.deserialize(data)
        if candidate.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise sqlite3.DatabaseError('The standalone SQLite snapshot fails its integrity check')
    return data
