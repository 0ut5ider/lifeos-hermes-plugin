# ABOUTME: Observes actual Atlas rendering before source replacement or owner revocation.
# ABOUTME: Checks withholding without replacing native collector or dashboard results.
import json
import os
from pathlib import Path
import sqlite3
import sys
from contextlib import closing

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode, view = sys.argv[2:4]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    expected = 'atlas_collect' if view == 'gear' else 'atlas_insights_view' if view == 'insights' else 'atlas_snapshot_view'
    if action == expected:
        rendered = True
        path = root.parent / '.local/state/lifeos/atlas/snapshot.json'
        if view == 'gear': path = root / 'LIFEOS/USER/GEAR.md'
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'created': path.write_text('{"assets":[]}')
        elif mode == 'source':
            before = path.stat()
            path.write_text(path.read_text().replace('SyntheticAtlasDevice', 'SyntheticAtlasChange'))
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        elif mode == 'metadata':
            before = path.stat()
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(path)
        elif mode == 'collector': (root / 'LIFEOS/USER/GEAR.md').write_text('## Synthetic changed devices\n')
        elif mode == 'cache': (root / 'LIFEOS/MEMORY/STATE/atlas-insights.json').write_text('{}')
        elif mode == 'graph':
            with closing(sqlite3.connect(path.parent / 'atlas.db')) as connection, connection:
                connection.execute("UPDATE asset SET display_name='SyntheticAtlasChangedGraph'")
        else: raise ValueError('Choose a declared Atlas observation')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    if view == 'gear':
        result = MemoryService(configuration).native(SessionContext('chat-a', '100', '200', 'private',
            ('owner',), 'local', 'atlas-observation'), 'atlas_collect', {'collector': 'gear'})
        if result.get('ok') is not True: raise RuntimeError('Atlas collector response is withheld')
    else:
        preferences.life_response('/api/atlas/insights' if view == 'insights' else '/api/atlas',
            account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False}))
