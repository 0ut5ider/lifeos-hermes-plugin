# ABOUTME: Runs real TELOS summary rendering with source and authority changes before publication.
# ABOUTME: Terminates after an actual summary write to verify durable artifact recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_telos as telos


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode = sys.argv[2]
    root = Path(configuration.load()['root'])
    real_native = NativeMemory._native

    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == 'telos_summary':
            if mode == 'authority':
                configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
            elif mode == 'source':
                path = root / 'LIFEOS/USER/TELOS/TELOS.md'
                path.write_text(path.read_text() + '\n## Wisdom\n- Synthetic concurrent wisdom\n')
        return result

    NativeMemory._native = native
    real_publish = telos.publish

    def publish(path, data):
        real_publish(path, data)
        if mode == 'interrupt':
            os._exit(73)

    telos.publish = publish
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    print(json.dumps(MemoryService(configuration).native(context, 'telos_summary',
        {'root': str(root / 'LIFEOS/USER/TELOS')})))


if __name__ == '__main__':
    main()
