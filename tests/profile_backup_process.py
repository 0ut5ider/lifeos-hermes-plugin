# ABOUTME: Runs real profile backup and competing native or SQLite writers in isolated processes.
# ABOUTME: Records observed lock refusal and interrupts publication through trace instrumentation.
from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import lifeos_hook_bridge.profile_backup as backup
from test_memory_native import OWNER


def wait(path):
    deadline = time.monotonic() + 20
    while not path.exists():
        if time.monotonic() > deadline:
            raise RuntimeError('The isolated profile-backup control did not release its barrier')
        time.sleep(0.01)


def run(settings):
    mode = settings['mode']
    markers = Path(settings['markers'])
    if mode in ('backup', 'interrupt'):
        collections = []
        observations = []
        def trace(frame, event, argument):
            if frame.f_code.co_filename != backup.__file__:
                return trace
            if mode == 'backup' and event == 'call' and frame.f_code.co_name == '_collect_profile':
                (markers / 'backup-ready').touch()
                wait(markers / 'release')
            if mode == 'backup' and event == 'return' and frame.f_code.co_name == '_collect_profile':
                collections.append(argument)
                (markers / 'collections.json').write_text(json.dumps(collections))
                path = Path(settings['database'])
                observations.append({'size': path.stat().st_size, 'mode': path.stat().st_mode, 'mtime_ns': path.stat().st_mtime_ns,
                    'sidecars': [p.name for p in path.parent.glob(path.name + '-*')]})
                (markers / 'observations.json').write_text(json.dumps(observations))
                (markers / f'collection-{len(collections)}-ready').touch()
                wait(markers / f'collection-{len(collections)}-release')
            if mode == 'interrupt' and event == 'line' and frame.f_code.co_name == 'create':
                if frame.f_locals.get('manifest') is not None and frame.f_locals.get('descriptor') is None:
                    stage = frame.f_locals['stage']
                    if (stage / 'manifest.json').exists() and frame.f_locals.get('signature'):
                        backup.inspect(MemoryConfiguration(Path(settings['configuration'])), stage,
                                       frame.f_locals['signature'])
                        (markers / 'interrupted-signature').write_text(frame.f_locals['signature'])
                        os._exit(73)
            return trace
        sys.settrace(trace)
        result = backup.create(MemoryConfiguration(Path(settings['configuration'])), Path(settings['destination']))
    elif mode in ('sqlite', 'native-sqlite-probe') or mode.startswith('sqlite-probe-'):
        database = NativeMemory(Path(settings['root'])).database if mode == 'native-sqlite-probe' else settings['database']
        with closing(sqlite3.connect(database, timeout=0)) as connection:
            try:
                connection.execute('BEGIN IMMEDIATE')
            except sqlite3.OperationalError as error:
                if 'locked' not in str(error):
                    raise
                (markers / (mode + '-blocked')).write_text(str(error))
            else:
                raise RuntimeError('The profile database writer bypasses the backup barrier')
            if mode == 'sqlite':
                connection.execute('PRAGMA busy_timeout=20000')
                connection.execute("INSERT INTO sessions VALUES ('later','Synthetic later concurrent history')")
                connection.commit()
        result = {'status': 'committed'}
    elif mode == 'native':
        memory = NativeMemory(Path(settings['root']))
        descriptor = os.open(memory.database.parent / 'memory-access.lock', os.O_RDWR)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                (markers / 'native-blocked').write_text(str(error))
            else:
                raise RuntimeError('The native writer bypasses the backup barrier')
        finally:
            os.close(descriptor)
        result = memory.remember(OWNER, category='project', content='Synthetic later concurrent native fact',
                                 title='Synthetic concurrent writer', project='lab', request_id='profile-later')
    else:
        raise ValueError('Unknown isolated profile-backup control')
    (markers / (mode + '-result.json')).write_text(json.dumps(result))


if __name__ == '__main__':
    run(json.loads(sys.stdin.read()))
