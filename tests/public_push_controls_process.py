# ABOUTME: Executes public publication guards through the actual Hermes tool dispatcher.
# ABOUTME: Uses disposable Git history and a false shell branch to prevent external publication.
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

from hermes_cli import plugins
from model_tools import handle_function_call
from tools.terminal_tool import cleanup_all_environments, set_approval_callback


home = Path.home()
profile = Path(os.environ['HERMES_HOME'])
project = home / 'project'
project.mkdir()
settings = Path(os.environ['LIFEOS_HOOK_SETTINGS'])
security = settings.parent / 'LIFEOS/USER/SECURITY'
security.mkdir(parents=True)
(security / 'PublicScrubPatterns.txt').write_text('PAIR_DENY_TOKEN\n')
trace = Path(__file__).resolve().parents[1] / 'scripts/paired_hook_trace.py'
encoded = base64.b64encode(('bun ' + os.environ['PAIR_NATIVE_GUARD']).encode()).decode()
hook_command = ' '.join([sys.executable, str(trace), 'run', 'PreToolUse.5.1', str(home / 'hooks.jsonl'), encoded])
settings.write_text(json.dumps({'permissions': {'allow': ['Bash']}, 'hooks': {'PreToolUse': [
    {'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': hook_command}]}]}}))
mode = os.environ['PAIR_APPROVAL_MODE']
command = 'printf PAIR_PUBLIC_ADMITTED; false && gh repo create fixture --public'
(profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']},
    'approvals': {'mode': 'off' if mode == 'off' else 'manual'},
    'command_allowlist': [command] if mode == 'permanent' else [], 'terminal': {'env_type': 'local'}}))


def git(*arguments):
    result = subprocess.run(['git', *arguments], cwd=project, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and not result.stderr, result
    return result.stdout


git('init', '--quiet')
git('config', 'user.name', 'Fixture')
git('config', 'user.email', 'fixture@example.invalid')
target = project / 'tracked.txt'
target.write_text('PAIR_PUBLIC_CONTENT\n')
git('add', 'tracked.txt')
git('commit', '--quiet', '-m', 'Clean fixture')
set_approval_callback(lambda *args, **kwargs: 'once')
plugins._reset_plugin_managers_for_tests()
plugins.discover_plugins()
rows = []
try:
    for name, blocked in [('clean', False), ('restricted', True), ('history', True), ('scan-failure', True)]:
        if name == 'restricted':
            target.write_text('PAIR_DENY_TOKEN\n')
            git('add', 'tracked.txt')
            git('commit', '--quiet', '-m', 'Restricted fixture')
        elif name == 'history':
            target.write_text('PAIR_PUBLIC_CONTENT\n')
            git('add', 'tracked.txt')
            git('commit', '--quiet', '-m', 'Clean current content')
        elif name == 'scan-failure':
            (security / 'PublicScrubPatterns.txt').write_text('[\n')
        result = handle_function_call('terminal', {'command': command, 'workdir': str(project), 'timeout': 10},
                                      task_id='public-guard', session_id='public-guard', tool_call_id=name)
        value = json.loads(result)
        evidence = os.environ.get('LIFEOS_PUBLIC_GUARD_EVIDENCE')
        if evidence:
            native = subprocess.run(['bun', os.environ['PAIR_NATIVE_GUARD']], input=json.dumps({
                'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': str(project)}),
                capture_output=True, text=True, timeout=20)
            retained = Path(evidence)
            (retained / (mode + '-' + name + '.json')).write_text(json.dumps({'result': value,
                'native': {'exit_code': native.returncode, 'stdout': native.stdout, 'stderr': native.stderr},
                'trace': (home / 'hooks.jsonl').read_text() if (home / 'hooks.jsonl').exists() else ''}, indent=2) + '\n')
        if blocked:
            assert value.get('error') and 'PublicPushGate' in value['error'], value
            assert 'PAIR_PUBLIC_ADMITTED' not in value.get('output', ''), value
        else:
            assert 'PAIR_PUBLIC_ADMITTED' in value['output'], value
        rows.append({'id': name, 'blocked': blocked, 'mode': mode, 'result': value})
finally:
    plugins.unload_plugins()
    cleanup_all_environments()
(home / 'public-results.json').write_text(json.dumps({'cases': rows}, indent=2) + '\n')
