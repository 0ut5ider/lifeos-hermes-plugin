# ABOUTME: Exercises real core-file publication with a controlled child process exit or owner revocation.
# ABOUTME: Keeps normal snapshot and atomic publication results intact in disposable synthetic profiles.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_access import NativeMemory
import lifeos_hook_bridge.memory_core_file as editor

configuration = Path(sys.argv[1])
root = Path(json.loads(configuration.read_text())['root'])
preferences = MemoryPreferences(configuration, root, Path(sys.executable), Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
request = json.loads(sys.argv[2])
mode = sys.argv[3]
original_publish = editor.publish
original_snapshot = editor._snapshot
observed = False


def interrupt(path, data, **options):
    original_publish(path, data, **options)
    if path == editor._path(NativeMemory(root, profile=configuration.parent), request['identifier']):
        os._exit(86)


def revoke(memory, scope, connection, identifier, **options):
    global observed
    result = original_snapshot(memory, scope, connection, identifier, **options)
    if not observed:
        observed = True
        preferences.configuration.update(lambda value: value['accounts'].clear())
    return result


if mode == 'interrupt': editor.publish = interrupt
elif mode == 'revoke': editor._snapshot = revoke
try:
    preferences.edit_core_file(request, account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    withheld = True
else:
    withheld = False
if mode == 'interrupt': raise SystemExit('The core save does not reach its interruption point')
print(json.dumps({'observed': observed, 'withheld': withheld}))
