# ABOUTME: Runs installed LifeOS permission rules around actual Hermes file and shell operations.
# ABOUTME: Records admitted effects and refused effects in a separate disposable process.
import json
import os
from pathlib import Path
import sys

from hermes_cli import plugins
from model_tools import handle_function_call
from tools.file_tools import read_file_tool
from tools.terminal_tool import cleanup_all_environments, set_approval_callback


def main():
    home = Path.home()
    profile = Path(os.environ['HERMES_HOME'])
    settings = Path(os.environ['LIFEOS_HOOK_SETTINGS'])
    settings.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    trace = []
    for tool in ('Write', 'Edit', 'MultiEdit', 'Bash'):
        for decision in ('allow', 'deny', 'ask-once', 'ask-deny'):
            name = tool + '-' + decision
            target = settings.parent / (name + '.txt')
            second = settings.parent / (name + '-second.txt')
            rule = 'ask' if decision.startswith('ask-') else decision
            command = 'touch ' + str(target)
            pattern = 'Bash(' + command + ')' if tool == 'Bash' else 'Edit(//' + str(target).lstrip('/') + ')'
            permissions = {'allow': ['Read'], rule: [pattern]}
            if rule == 'allow':
                permissions['allow'] = ['Read', pattern]
            settings.write_text(json.dumps({'permissions': permissions, 'hooks': {
                'PermissionRequest': [{'matcher': 'Bash|Write|Edit|MultiEdit', 'hooks': [
                    {'type': 'command', 'command': 'bun ' + os.environ['PAIR_NATIVE_SAFETY']}]}]}}))
            (profile / 'config.yaml').write_text(json.dumps({
                'plugins': {'enabled': ['lifeos-hook-bridge']}, 'approvals': {'mode': 'manual'},
                'terminal': {'env_type': 'local'}}))
            callbacks = []

            def approve(command, description, **kwargs):
                callbacks.append({'command': command, 'description': description})
                return 'once' if decision == 'ask-once' else 'deny'

            set_approval_callback(approve)
            plugins._reset_plugin_managers_for_tests()
            plugins.discover_plugins()
            task = 'permission-' + name
            if tool in ('Edit', 'MultiEdit'):
                target.write_text('OLD\n')
                read_file_tool(str(target), task_id=task)
            if tool == 'Write':
                function, arguments = 'write_file', {'path': str(target), 'content': 'NEW'}
            elif tool == 'Edit':
                function, arguments = 'patch', {'mode': 'replace', 'path': str(target),
                                               'old_string': 'OLD', 'new_string': 'NEW'}
            elif tool == 'MultiEdit':
                second.write_text('SECOND\n')
                read_file_tool(str(second), task_id=task)
                text = ('*** Begin Patch\n*** Update File: ' + str(second)
                        + '\n-SECOND\n+APPLIED\n*** Update File: ' + str(target)
                        + '\n-OLD\n+NEW\n*** End Patch')
                function, arguments = 'patch', {'mode': 'patch', 'patch': text}
            else:
                function, arguments = 'terminal', {'command': command, 'workdir': str(home), 'timeout': 10}
            result = handle_function_call(function, arguments, task_id=task,
                                          session_id=name, tool_call_id=name)
            admitted = decision in ('allow', 'ask-once')
            expected = '' if tool == 'Bash' else 'NEW'
            changed = target.exists() and target.read_text().strip() == expected
            assert changed is admitted, (name, result, target.read_text() if target.exists() else None)
            if tool == 'MultiEdit':
                assert second.read_text().strip() == ('APPLIED' if admitted else 'SECOND'), (name, result)
            assert bool(callbacks) is decision.startswith('ask-'), (name, callbacks, result)
            cases.append({'id': name, 'admitted': admitted, 'effect_matches': True,
                          'approval_callbacks': len(callbacks), 'verified': True})
            trace.append({'id': name, 'arguments': arguments, 'result': result, 'callbacks': callbacks})
            plugins.unload_plugins()
            cleanup_all_environments()
    (home / 'permission-results.json').write_text(json.dumps({'cases': cases}, indent=2) + '\n')
    with (home / 'permission-trace.jsonl').open('w') as output:
        for row in trace:
            output.write(json.dumps(row) + '\n')


def mcp():
    from tools.mcp_tool_discovery import register_mcp_servers
    from tools.mcp_tool_lifecycle import shutdown_mcp_servers
    home = Path.home()
    profile = Path(os.environ['HERMES_HOME'])
    settings = Path(os.environ['LIFEOS_HOOK_SETTINGS'])
    settings.parent.mkdir(parents=True)
    server = Path(__file__).resolve().parents[1] / 'scripts/paired_mcp_server.py'
    (profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']},
                                                   'approvals': {'mode': 'manual'}}))
    names = register_mcp_servers({'permission': {'command': sys.executable, 'args': [str(server)]}})
    assert 'mcp__permission__ping' in names, names
    try:
        rows = []
        for decision in ('allow', 'deny', 'ask-once', 'ask-deny'):
            rule = 'ask' if decision.startswith('ask-') else decision
            settings.write_text(json.dumps({'permissions': {rule: ['mcp__permission__ping']},
                'hooks': {'PermissionRequest': [{'matcher': 'mcp__.*', 'hooks': [
                    {'type': 'command', 'command': 'bun ' + os.environ['PAIR_NATIVE_SAFETY']}]}]}}))
            callbacks = []

            def approve(command, description, **kwargs):
                callbacks.append(command)
                return 'once' if decision == 'ask-once' else 'deny'

            set_approval_callback(approve)
            plugins._reset_plugin_managers_for_tests()
            plugins.discover_plugins()
            result = handle_function_call('mcp__permission__ping', {}, session_id=decision, tool_call_id=decision)
            executed = 'PAIR_MCP_212' in result
            assert executed is (decision in ('allow', 'ask-once')), (decision, result)
            assert len(callbacks) == int(decision.startswith('ask-')), (decision, callbacks, result)
            rows.append({'id': decision, 'executed': executed, 'approval_callbacks': len(callbacks), 'result': result})
            plugins.unload_plugins()
        (home / 'mcp-results.json').write_text(json.dumps({'cases': rows}, indent=2) + '\n')
    finally:
        shutdown_mcp_servers()


if __name__ == '__main__':
    try:
        mcp() if len(sys.argv) > 1 and sys.argv[1] == 'mcp' else main()
    finally:
        plugins.unload_plugins()
        set_approval_callback(None)
        cleanup_all_environments()
