# ABOUTME: Changes current hash inputs after actual native token rendering.
# ABOUTME: Interrupts fixed environment publication to verify the native recovery journal.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_deny_hashes as hashes


configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = []


def native(memory, action, **arguments):
    result = original(memory, action, **arguments)
    if action == 'deny_hashes':
        rendered.append(result)
        if mode in ('source', 'private'):
            path = root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
            content = ('# Synthetic principal\n<private>FixtureSurname FixtureGivenname</private>\n'
                       if mode == 'private' else path.read_text() + '\nSynthetic later hash edit\n')
            path.write_text(content)
        elif mode == 'authority':
            configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        elif mode in ('environment', 'environment_large'):
            path = root / '.env'
            path.write_text(path.read_text() + 'SYNTHETIC_LATER=' +
                            ('x' * (256 * 1024) if mode == 'environment_large' else 'fixture') + '\n')
        elif mode == 'marker':
            (root / 'skills/_LIFEOS').rmdir()
    return result


NativeMemory._native = native
original_publish = hashes.publish


def publish(path, data):
    original_publish(path, data)
    if mode == 'interrupt':
        os._exit(73)


hashes.publish = publish
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
result = MemoryService(configuration).native(context, 'deny_hashes', {'args': ['--show-tokens']})
assert len(rendered) == 1
assert 'fixturesurname fixturegivenname' in rendered[0]['tokens']
print(json.dumps(result))
