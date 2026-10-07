# ABOUTME: Changes sources or owner authority after actual native interview rendering.
# ABOUTME: Exits after fixed interview publication to verify durable recovery.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_interview as interview


def main():
    configuration = MemoryConfiguration(Path(sys.argv[1]))
    mode, operation = sys.argv[2:4]
    root = Path(configuration.load()['root'])
    context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
    service = MemoryService(configuration)
    now = '2026-10-04T00:00:00Z'
    relative = interview.STATE if operation == 'interview_due_mark' else interview.CACHE
    arguments = {'now': now, 'path': str(root / relative)}
    if operation == 'interview_due_cache_write':
        inputs = service.native(context, 'interview_due_inputs', {'now': now, 'evidence_present': False})['value']
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m.computeVerdict(JSON.parse(process.argv[2]),new Date(process.argv[3]))));'
        import subprocess
        result = subprocess.run(['bun', '--no-install', '-e', program, str(root / 'LIFEOS/TOOLS/InterviewDue.ts'),
            json.dumps(inputs), now], capture_output=True, text=True, check=True)
        arguments = {'path': str(root / relative), 'verdict': json.loads(result.stdout)}
    if operation == 'interview_due_inputs':
        arguments = {'now': now, 'evidence_present': False}
    original = NativeMemory._native

    def native(memory, action, **values):
        result = original(memory, action, **values)
        if action == ('interview_completion' if operation == 'interview_due_mark' else 'interview_due'):
            if mode == 'authority':
                configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
            elif mode.startswith('source'):
                path = root / interview.STATE
                content = json.loads(path.read_text())
                content['synthetic_later'] = ('x' * (256 * 1024) if mode == 'source_large' else
                    '<private>Synthetic later private completion</private>' if mode == 'source_excluded' else
                    'Synthetic later completion edit')
                path.write_text(json.dumps(content))
        return result

    NativeMemory._native = native
    original_publish = interview.publish

    def publish(path, data):
        original_publish(path, data)
        if mode == 'interrupt':
            os._exit(73)

    interview.publish = publish
    print(json.dumps(service.native(context, operation, arguments)))


if __name__ == '__main__':
    main()
