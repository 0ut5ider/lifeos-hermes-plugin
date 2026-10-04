# ABOUTME: Changes sources or owner authority after the actual native freshness renderer runs.
# ABOUTME: Exits after publication to exercise durable recovery of user and system artifacts.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_freshness as freshness
import lifeos_hook_bridge.memory_freshness_cache as cache


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode, operation, relative = sys.argv[2:5]
    root = Path(configuration.load()['root'])
    real_native = NativeMemory._native
    action_name = 'freshness_write' if operation == 'write_freshness' else 'freshness_cache'

    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == action_name:
            if mode == 'authority':
                configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
            elif mode == 'source':
                path = root / relative
                path.write_text(path.read_text() + '\nSynthetic later source edit\n')
            elif mode == 'source_excluded':
                path = root / relative
                path.write_text(path.read_text() + '\n<private>Synthetic later excluded edit</private>\n')
        return result

    NativeMemory._native = native
    module = freshness if operation == 'write_freshness' else cache
    real_publish = module.publish if operation != 'write_freshness' else None
    if operation == 'write_freshness':
        import lifeos_hook_bridge.memory_transaction as transaction
        module = transaction
        real_publish = transaction.publish

    def publish(path, data):
        real_publish(path, data)
        if mode == 'interrupt' and str(path) == str(root / relative):
            os._exit(73)

    module.publish = publish
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    arguments = {'kind': 'context', 'path': str(root / relative), 'by': 'synthetic-writer', 'slug': None}
    print(json.dumps(MemoryService(configuration).native(context, operation,
        arguments if operation == 'write_freshness' else {})))


if __name__ == '__main__':
    main()
