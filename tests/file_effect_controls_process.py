# ABOUTME: Applies actual file operations and measures native Atlas, Knowledge, and complexity effects.
# ABOUTME: Keeps direct native hook controls distinct from the installed Hermes dispatcher.
import json
import os
from pathlib import Path
import subprocess

from hermes_cli import plugins
from model_tools import handle_function_call
from tools.file_tools import patch_tool, read_file_tool, write_file_tool
from tools.terminal_tool import cleanup_all_environments


home = Path.home()
root = home / '.claude'
profile = Path(os.environ['HERMES_HOME'])
source = Path(os.environ['PAIR_FILE_SOURCE'])
side = os.environ['PAIR_FILE_SIDE']
settings = Path(os.environ['LIFEOS_HOOK_SETTINGS'])
root.mkdir(exist_ok=True)
(profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']},
                                               'terminal': {'env_type': 'local'}}))
settings.write_text('{"hooks":{}}')
if side == 'hermes':
    plugins._reset_plugin_managers_for_tests()
    plugins.discover_plugins()


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def operation(tool, path, content, session, program):
    settings.write_text(json.dumps({'permissions': {'allow': ['Read', 'Edit']}, 'hooks': {'PostToolUse': [
        {'matcher': 'Write|Edit|MultiEdit', 'hooks': [{'type': 'command', 'command': 'bun ' + str(source / 'hooks' / (program + '.hook.ts'))}]}]}}))
    path.parent.mkdir(parents=True, exist_ok=True)
    task = session
    if tool != 'Write':
        path.write_text('OLD\n')
        result = json.loads(read_file_tool(str(path), task_id=task))
        assert not result.get('error'), result
    if tool == 'Write':
        name, args = 'write_file', {'path': str(path), 'content': content}
        native_input = {'file_path': str(path), 'content': content}
    elif tool == 'Edit':
        name, args = 'patch', {'mode': 'replace', 'path': str(path), 'old_string': 'OLD', 'new_string': content}
        native_input = {'file_path': str(path), 'old_string': 'OLD', 'new_string': content}
    else:
        text = '*** Begin Patch\n*** Update File: ' + str(path) + '\n-OLD\n' + ''.join('+' + line + '\n' for line in content.splitlines()) + '*** End Patch'
        name, args = 'patch', {'mode': 'patch', 'patch': text}
        native_input = {'file_path': str(path), 'edits': [{'old_string': 'OLD', 'new_string': content}]}
    if side == 'hermes':
        result = handle_function_call(name, args, task_id=task, session_id=session, tool_call_id=session)
        value, _ = json.JSONDecoder().raw_decode(result)
        assert not value.get('error'), value
        context = result[json.JSONDecoder().raw_decode(result)[1]:].strip()
    else:
        result = write_file_tool(**args, task_id=task) if tool == 'Write' else patch_tool(**args, task_id=task)
        value = json.loads(result)
        assert not value.get('error'), value
        process = subprocess.run(['bun', str(source / 'hooks' / (program + '.hook.ts'))],
            input=json.dumps({'hook_event_name': 'PostToolUse', 'tool_name': tool, 'tool_input': native_input,
                              'session_id': session, 'tool_response': value, 'cwd': str(home)}),
            env=os.environ.copy(), capture_output=True, text=True, timeout=20)
        assert process.returncode == 0 and not process.stderr, process
        output = json.loads(process.stdout) if process.stdout.strip() else {}
        context = output.get('hookSpecificOutput', {}).get('additionalContext', '')
    assert path.read_text().strip() == content.strip(), (path, content, path.read_text())
    return context, args, result


valid = ('---\nid: kb_fixture\ntype: idea\ntitle: Fixture\ntags: [fixture]\nquality: 3\n'
         'created: 2026-10-06\nupdated: 2026-10-06\nconvention: kb-v3\n---\n# Fixture\n')
rows = []
try:
    for tool in ('Write', 'Edit', 'MultiEdit'):
        for name, relative, expected in (
            ('projects', 'project/PROJECTS.md', 'projects'), ('gear', 'project/GEAR.md', 'gear'),
            ('inventory', 'project/infra-inventory.ts', 'infra-inventory'),
            ('systemd', '.config/systemd/user/com.lifeos.fixture.service', 'systemd'),
            ('unrelated', 'project/ordinary.txt', None)):
            session = 'atlas-' + tool + '-' + name
            events = home / '.local/state/lifeos/atlas/events.jsonl'
            before = len(events.read_text().splitlines()) if events.exists() else 0
            context, args, result = operation(tool, home / relative, 'PAIR_FILE_EFFECT', session, 'AtlasEventCapture')
            after = [json.loads(line) for line in events.read_text().splitlines()[before:]] if events.exists() else []
            assert [r['source'] for r in after] == ([expected] if expected else []), after
            expected_tool = 'Edit' if side == 'hermes' and tool == 'MultiEdit' else tool
            assert all(r['tool'] == expected_tool for r in after), after
            rows.append({'id': session, 'sources': [r['source'] for r in after], 'applied': True,
                         'native_tool': expected_tool, 'context': context, 'arguments': args, 'result': result})
        for name, relative, content, warning in (
            ('valid', '.claude/LIFEOS/MEMORY/KNOWLEDGE/Ideas/valid.md', valid, False),
            ('invalid', '.claude/LIFEOS/MEMORY/KNOWLEDGE/Ideas/invalid.md', '# Off schema', True),
            ('index', '.claude/LIFEOS/MEMORY/KNOWLEDGE/Ideas/_index.md', '# Index', False),
            ('outside', 'project/outside.md', '# Outside', False)):
            session = 'knowledge-' + tool + '-' + name
            context, args, result = operation(tool, home / relative, content, session, 'KnowledgeWriteGuard')
            assert ('Knowledge note written off-schema' in context) is warning, (session, context)
            rows.append({'id': session, 'warning': warning, 'applied': True,
                         'context': context, 'arguments': args, 'result': result})
        for net in (199, 200, 201):
            session = 'complexity-' + tool + '-' + str(net)
            lines = net if tool == 'Write' else net + 1
            content = '\n'.join('line ' + str(i) for i in range(lines))
            context, args, result = operation(tool, home / ('project/' + session + '.ts'), content, session, 'ComplexityRatchet')
            state = read(root / 'LIFEOS/MEMORY/STATE/complexity-ratchet' / (session + '.json'))
            assert state['cumulative'] == net and state['deps'] == 0, (session, state)
            assert ('COMPLEXITY RATCHET' in context) is (net > 200), (session, context)
            rows.append({'id': session, 'state': state, 'warning': net > 200, 'applied': True,
                         'context': context, 'arguments': args, 'result': result})
        session = 'dependencies-' + tool
        content = '{\n  "fixture-dependency": "^1.2.3"\n}'
        context, args, result = operation(tool, home / 'project/package.json', content, session, 'ComplexityRatchet')
        state = read(root / 'LIFEOS/MEMORY/STATE/complexity-ratchet' / (session + '.json'))
        assert state['deps'] == 1 and 'COMPLEXITY RATCHET' in context, (session, state, context)
        rows.append({'id': session, 'state': state, 'warning': True, 'applied': True,
                     'context': context, 'arguments': args, 'result': result})
finally:
    if side == 'hermes':
        plugins.unload_plugins()
    cleanup_all_environments()
(home / 'file-results.json').write_text(json.dumps({'cases': rows}, indent=2) + '\n')
