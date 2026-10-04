# ABOUTME: Runs actual native state rendering with real source and authority interleavings.
# ABOUTME: Terminates the process after publication to exercise durable journal recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_state as state


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode = sys.argv[2]
    root = Path(configuration.load()['root'])
    real_native = NativeMemory._native

    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == 'lifeos_state':
            if mode == 'authority':
                configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
            elif mode == 'source':
                path = root / 'LIFEOS/USER/TELOS/CURRENT_STATE/HEALTH.md'
                path.write_text(path.read_text() + '\nstatus: have\n')
        return result

    NativeMemory._native = native
    real_publish = state.publish

    def publish(path, data):
        real_publish(path, data)
        if mode == 'interrupt':
            os._exit(73)

    state.publish = publish
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    print(json.dumps(MemoryService(configuration).native(context, 'lifeos_state',
        {'root': str(root / 'LIFEOS'), 'json_output': True})))


if __name__ == '__main__':
    main()
