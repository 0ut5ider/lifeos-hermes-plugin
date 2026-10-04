# ABOUTME: Runs real migration rendering with source and authority changes before publication.
# ABOUTME: Exits after the first source publication to test recovery of sources and backups.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_freshness_migration as migration


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode = sys.argv[2]
    root = Path(configuration.load()['root'])
    target = root / (sys.argv[3] if len(sys.argv) > 3 else 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md')
    real_native = NativeMemory._native

    def native(memory, action, **arguments):
        result = real_native(memory, action, **arguments)
        if action == 'freshness_migration':
            if mode == 'authority':
                configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
            elif mode == 'source':
                target.write_text(target.read_text() + '\nSynthetic later migration edit\n')
        return result

    NativeMemory._native = native
    real_publish = migration.publish

    def publish(path, data):
        real_publish(path, data)
        if mode == 'interrupt' and str(path) == str(target):
            os._exit(73)

    migration.publish = publish
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    print(json.dumps(MemoryService(configuration).native(context, 'freshness_migration',
        {'dry_run': False, 'state': False})))


if __name__ == '__main__':
    main()
