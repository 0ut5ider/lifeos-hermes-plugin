# ABOUTME: Interrupts actual Conduit default publication to exercise native owner recovery.
# ABOUTME: Verifies recovery removes an incomplete default and preserves a later owner edit.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge import memory_conduit
from lifeos_hook_bridge.memory_access import NativeMemory, MemoryUnavailable
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
config = root / memory_conduit.CONFIG
original = memory_conduit.publish
published = False


def interrupt(path, data):
    global published
    original(path, data)
    published = True
    raise MemoryUnavailable('Synthetic interruption after actual default publication')


memory_conduit.publish = interrupt
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
withheld = False
try:
    preferences.life_response('/api/conduit/today', account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    withheld = True
memory_conduit.publish = original
memory = NativeMemory(root)
output = {'published': published, 'withheld': withheld, 'journaled': memory.transaction.journal.is_file()}
if mode == 'later-edit':
    edited = '{"pollIntervalSec":60,"synthetic":"SyntheticConduitLaterEdit"}'
    config.write_text(edited)
    refused = False
    try:
        with memory._transaction(): pass
    except MemoryUnavailable:
        refused = True
    output.update(recovery_refuses_later_edit=refused, later_edit_preserved=config.read_text() == edited)
elif mode == 'interrupted':
    with memory._transaction(): pass
    output['recovered_absence'] = not config.exists() and not memory.transaction.journal.exists()
    result = preferences.life_response('/api/conduit/today', account='dashboard:basic:synthetic-owner')
    output.update(retried=result[0]['status'] == 200, private=config.stat().st_mode & 0o777 == 0o600)
else:
    raise ValueError('Choose an interrupted or later-edit publication observation')
print(json.dumps(output))
