# ABOUTME: Inserts real destination edits between PULSE collection and publication.
# ABOUTME: Records whether governed publication preserves the later file bytes.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_pulse_adapters as adapters


configuration = MemoryConfiguration(Path(sys.argv[1]))
root = Path(configuration.load()['root'])
mode = sys.argv[2]
original_publish = adapters._publish
target = root / (adapters.LOG if mode == 'log' else adapters.DATA + 'synthetic.json')
later = b'{"synthetic_later":"preserved"}\n'


def publish(*args, **kwargs):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(later)
    return original_publish(*args, **kwargs)


adapters._publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
service = MemoryService(configuration)
if mode == 'log':
    result = service.native(context, 'pulse_adapter_log', {'entry': {'synthetic_attempt': 'append'}})
else:
    page = json.loads(target.read_text())
    page['data']['title'] = 'Synthetic replacement page'
    result = service.native(context, 'pulse_data', {'action': 'write_page', 'identifier': 'synthetic', 'value': page})
print(json.dumps({'result': result, 'preserved': target.read_bytes() == later}))
