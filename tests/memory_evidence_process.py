# ABOUTME: Changes JSON sources or owner authority after actual native evidence rendering.
# ABOUTME: Exits after cache publication to exercise durable interruption recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_evidence as evidence


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode, operation, relative = sys.argv[2:5]
    root = Path(configuration.load()['root'])
    service = MemoryService(configuration)
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    now = '2026-10-04T00:00:00Z'
    arguments = {'domain': None, 'now': now}
    if operation == 'state_evidence_cache_write':
        payload = service.native(context, 'state_evidence_read', arguments)['value']
        arguments = {'path': str(root / evidence.OUTPUT), 'evidence': payload}
    native = NativeMemory._native

    def render(memory, action, **values):
        result = native(memory, action, **values)
        if action == 'state_evidence':
            if mode == 'authority':
                configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
            elif mode in {'source', 'source_excluded'}:
                path = root / relative
                content = json.loads(path.read_text())
                content['synthetic_later'] = ('<private>Synthetic later excluded evidence edit</private>'
                                              if mode == 'source_excluded' else 'Synthetic later evidence edit')
                path.write_text(json.dumps(content))
        return result

    NativeMemory._native = render
    native_publish = evidence.publish

    def publish(path, data):
        native_publish(path, data)
        if mode == 'interrupt':
            os._exit(73)

    evidence.publish = publish
    print(json.dumps(service.native(context, operation, arguments)))


if __name__ == '__main__':
    main()
