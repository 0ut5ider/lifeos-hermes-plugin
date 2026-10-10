# ABOUTME: Runs actual TELOS saves with controlled process interruption or owner revocation.
# ABOUTME: Observes original source collection and atomic publication without replacing their results.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_preferences import MemoryPreferences
import lifeos_hook_bridge.memory_telos_file as editor

configuration = Path(sys.argv[1])
root = Path(json.loads(configuration.read_text())['root'])
preferences = MemoryPreferences(configuration, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
mode = sys.argv[3]
observed = False
original_publish = editor.publish
original_snapshot = editor._snapshot


def interrupt(path, data, **options):
    original_publish(path, data, **options)
    if path.name == 'GOALS.md': os._exit(86)


def revoke(memory, scope, connection, filename):
    global observed
    result = original_snapshot(memory, scope, connection, filename)
    if not observed:
        observed = True
        preferences.configuration.update(lambda value: value['accounts'].clear())
    return result


if mode == 'interrupt': editor.publish = interrupt
elif mode == 'revoke': editor._snapshot = revoke
try:
    preferences.edit_telos_file(json.loads(sys.argv[2]), account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    withheld = True
else:
    withheld = False
if mode == 'interrupt': raise SystemExit('The TELOS save does not reach its interruption point')
print(json.dumps({'observed': observed, 'withheld': withheld}))
