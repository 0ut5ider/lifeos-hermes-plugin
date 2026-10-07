# ABOUTME: Instruments actual native graph rendering and publication in a separate process.
# ABOUTME: Changes real synthetic authority or sources and exits between real artifact writes.
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_graph as graph


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode = sys.argv[2]
    real_native = NativeMemory._native

    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == 'memory_graph':
            if mode == 'authority':
                configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
            elif mode == 'source':
                path = memory.root / 'LIFEOS/MEMORY/WORK/synthetic-work/ISA.md'
                path.write_text(path.read_text() + '\nSynthetic concurrent graph source edit\n')
        return result

    NativeMemory._native = native
    real_publish = graph.publish

    def publish(path, data):
        real_publish(path, data)
        if mode == 'interrupt':
            os._exit(73)

    graph.publish = publish
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    root = configuration.load()['root']
    result = MemoryService(configuration).native(context, 'memory_graph',
        {'root': str(Path(root) / 'LIFEOS/MEMORY'), 'command': 'build', 'layer': 'declared', 'target': None})
    print(json.dumps({'context': asdict(context), 'result': result}))


if __name__ == '__main__':
    main()
