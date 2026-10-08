# ABOUTME: Changes permission after real native reads and validation complete.
# ABOUTME: Records publication actions to measure refusal before a native writer runs.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import lifeos_hook_bridge.memory_proposals as proposals


configuration = MemoryConfiguration(Path(sys.argv[1]))
request = json.load(sys.stdin)
actions = []
revoked = False
observations = 0


def observe(action):
    global revoked, observations
    actions.append(action)
    if action == request['trigger']:
        observations += 1
    if request['revoke'] and not revoked and observations == request['trigger_count'] and action == request['trigger']:
        configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        revoked = True
        actions.append('authority_revoked')


real_native = NativeMemory._native


def native(memory, action, **arguments):
    result = real_native(memory, action, **arguments)
    observe(action)
    return result


NativeMemory._native = native
real_row = proposals._current_row


def current_row(memory, record):
    result = real_row(memory, record)
    observe('proposal_read')
    return result


proposals._current_row = current_row
real_content = NativeMemory._content


def content(memory, record, *arguments, **keywords):
    result = real_content(memory, record, *arguments, **keywords)
    observe('content_read')
    return result


NativeMemory._content = content
real_target = NativeMemory._target


def target(memory, connection, scope, reference):
    result = real_target(memory, connection, scope, reference)
    observe('target_read')
    return result


NativeMemory._target = target
context = SessionContext('chat-a', '100', '200', 'private', ('owner',), 'local', 'native-session')
service = MemoryService(configuration)
method = service.native if request['interface'] == 'native' else service.call_context
result = method(context, request['operation'], request['arguments'])
print(json.dumps({'result': result, 'actions': actions, 'revoked': revoked}))
