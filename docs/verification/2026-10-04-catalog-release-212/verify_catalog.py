# ABOUTME: Checks actual installed catalog dispatch and native Safety context delivery.
# ABOUTME: Uses a synthetic profile and existing dependencies without invoking Hermes bootstrap.
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import site
import subprocess
import sys
import tempfile


def verify(host, profile, native, release):
    host, profile, native, release = map(Path, (host, profile, native, release))
    key = hashlib.sha256(str(host.resolve()).encode()).hexdigest()[:16]
    facts = json.loads((profile / 'installs' / key / 'facts.json').read_text())
    environment = Path(facts['packages']['venv']['environment'])
    sites = list((environment / 'lib').glob('python*/site-packages'))
    assert len(sites) == 1
    fixture = Path(tempfile.mkdtemp(prefix='catalog-control-', dir=release))
    hooks = fixture / '.claude/settings.json'
    hooks.parent.mkdir()
    hermes = fixture / '.hermes'
    hermes.mkdir()
    (hermes / 'plugins').symlink_to(profile / 'plugins', target_is_directory=True)
    (hermes / 'config.yaml').write_text(json.dumps({
        'plugins': {'enabled': ['lifeos-hook-bridge']},
        'tools': {'tool_search': {'enabled': 'on'}},
    }))
    command = 'bun ' + shlex.quote(str(native / 'hooks/Safety.hook.ts'))
    encoded = base64.b64encode(command.encode()).decode()
    trace = fixture / 'hooks.jsonl'
    tracer = release / 'plugin-source/scripts/paired_hook_trace.py'
    wrapper = ' '.join(shlex.quote(value) for value in (
        '/usr/bin/python3', str(tracer), 'run', 'PostToolUse.5.1', str(trace), encoded))
    hooks.write_text(json.dumps({'hooks': {'PostToolUse': [{
        'matcher': 'ToolSearch', 'hooks': [{'type': 'command', 'command': wrapper}],
    }]}}))
    driver = fixture / 'dispatch.py'
    result_path = fixture / 'result.json'
    driver.write_text(
        '# ABOUTME: Executes an installed catalog search with the real plugin and native Safety hook.\n'
        '# ABOUTME: Stores the caller-visible result without a model completion.\n'
        'import site,sys,json\nfrom pathlib import Path\n'
        f'site.addsitedir({str(sites[0])!r})\nsys.path.insert(0,{str(host)!r})\n'
        'from model_tools import handle_function_call\n'
        'result=handle_function_call("tool_search",{"queries":["todo"]},'
        'enabled_toolsets=["todo"],session_id="catalog-installed-control",tool_call_id="search-one")\n'
        f'Path({str(result_path)!r}).write_text(json.dumps({{"result":result}}))\n')
    env = {key: value for key, value in os.environ.items() if key in {'PATH', 'LANG', 'TZ'}}
    env.update(HOME=str(fixture), HERMES_HOME=str(hermes), LIFEOS_HOOK_SETTINGS=str(hooks),
               LIFEOS_DIR=str(fixture / '.claude/LIFEOS'), LIFEOS_CONFIG_DIR=str(hooks.parent),
               PYTHONDONTWRITEBYTECODE='1')
    run = subprocess.run([sys.executable, str(driver)], cwd=fixture, env=env,
                         capture_output=True, text=True, timeout=90)
    (fixture / 'stdout.txt').write_text(run.stdout)
    (fixture / 'stderr.txt').write_text(run.stderr)
    assert run.returncode == 0, f'Catalog process exits {run.returncode}; inspect {fixture.name}'
    assert trace.exists(), 'Catalog result does not invoke native Safety'
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]['exit_code'] == 0
    payload = json.loads(base64.b64decode(rows[0]['stdin_base64']))
    assert payload['tool_name'] == 'ToolSearch' and payload['tool_input'] == {'queries': ['todo']}
    assert 'todo_list' in payload['tool_response']['tools']
    output = json.loads(rows[0]['stdout'])
    context = output['hookSpecificOutput']['additionalContext'].strip()
    assert context and context in json.loads(result_path.read_text())['result']
    record = {'exit_code': 0, 'hook_invocations': 1, 'native_safety_exit': 0,
              'native_safety_context_delivered': True, 'model_completion_used': False,
              'stdout_sha256': rows[0]['stdout_sha256'], 'fixture': str(fixture),
              'model_tools_sha256': hashlib.sha256((host / 'model_tools.py').read_bytes()).hexdigest()}
    print(json.dumps(record))
    return record


if __name__ == '__main__':
    verify(*sys.argv[1:])
