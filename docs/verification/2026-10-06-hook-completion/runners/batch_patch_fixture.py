# ABOUTME: Exercises real Hermes multi-file patches and native batch-shaped hook inputs.
# ABOUTME: Uses an operating-system write denial to verify partial failure and checkpoint suppression.

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import paired_lifecycle_effects as driver


PROGRAMS = ('ISASync', 'ISAStaleWriteGuard', 'CheckpointPerISC', 'ConfigEvalFire',
            'AtlasEventCapture', 'KnowledgeWriteGuard', 'ComplexityRatchet')


def run_host(side, partial):
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from model_tools import handle_function_call
    from tools.file_tools import patch_tool, read_file_tool
    from tools.terminal_tool import cleanup_all_environments

    home = Path(os.environ['HOME'])
    root = home / '.claude'
    session = 'batch-fixture'
    plan = json.loads((home / 'plan.json').read_text())
    task_id = 'batch-task'
    for item in plan:
        result = json.loads(read_file_tool(item['path'], task_id=task_id))
        assert not result.get('error'), result
    if side == 'hermes':
        discover_plugins()
    patch_text = '*** Begin Patch\n' + ''.join(
        '*** Update File: ' + item['path'] + '\n' + ''.join(
            '@@\n' + ''.join('-' + line + '\n' for line in edit['old_string'].splitlines())
            + ''.join('+' + line + '\n' for line in edit['new_string'].splitlines()) for edit in item['edits'])
        for item in plan) + '*** End Patch'
    args = {'mode': 'patch', 'patch': patch_text}
    try:
        result = (handle_function_call('patch', args, task_id=task_id, session_id=session, tool_call_id='batch-call')
                  if side == 'hermes' else patch_tool(**args, task_id=task_id))
        (home / 'tool-result.txt').write_text(result)
        # The plugin appends context after the original JSON tool result.
        decoder = json.JSONDecoder()
        outcome, _ = decoder.raw_decode(result)
        assert outcome['success'] is not partial, outcome
        applied = outcome['files_modified']
        assert applied == [item['path'] for item in plan[:1 if partial else len(plan)]], outcome
        if partial:
            assert 'Permission denied' in outcome['error'], outcome
        for index, item in enumerate(plan):
            content = Path(item['path']).read_text()
            expected = item['before']
            if item['path'] in applied:
                for edit in item['edits']:
                    expected = expected.replace(edit['old_string'], edit['new_string'])
            assert content.rstrip('\n') == expected.rstrip('\n'), (index, content, expected)
        if side == 'native':
            for item in plan:
                if item['path'] not in applied:
                    continue
                payload = {'hook_event_name': 'PostToolUse', 'session_id': session, 'tool_name': 'MultiEdit',
                           'tool_input': {'file_path': item['path'], 'edits': item['edits']},
                           'tool_response': {'success': True}, 'cwd': str(home / 'project')}
                for number, program in enumerate(PROGRAMS, 1):
                    if partial and program == 'CheckpointPerISC':
                        continue
                    command = ['bun', str(root / 'hooks' / (program + '.hook.ts'))]
                    run = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, timeout=25)
                    assert run.returncode == 0, (program, run.stderr)
                    with (home / 'hooks.jsonl').open('a') as log:
                        log.write(json.dumps({'id': f'PostToolUse.10.{number}', 'event': 'PostToolUse',
                                              'stdin_base64': base64.b64encode(json.dumps(payload).encode()).decode(),
                                              'stdout': run.stdout, 'stderr': run.stderr, 'exit_code': run.returncode}) + '\n')
        lifeos = root / 'LIFEOS'
        isa = Path(plan[0]['path'])
        content = isa.read_text()
        checkpoint = isa.parent / '.checkpoint-state.json'
        repo = home / 'checkpoint-repo'
        view = driver.read_json(lifeos / 'MEMORY/STATE/isa-session-view' / (session + '.json'))['views']
        complexity = driver.read_json(lifeos / 'MEMORY/STATE/complexity-ratchet' / (session + '.json'))
        traces = driver.read_json_lines(home / 'hooks.jsonl')
        expected_calls = (len(PROGRAMS) - 1) if partial else len(PROGRAMS) * len(plan)
        assert len(traces) == expected_calls, [(r['id'], r.get('stdout')) for r in traces]
        result = {'isa_closed': '- [x] ISC-1:' in content,
                  'view_matches_content': view[str(isa)] == hashlib.sha256(content.encode()).hexdigest(),
                  'registry_present': 'pair-run' in driver.read_json(lifeos / 'MEMORY/STATE/work.json')['sessions'],
                  'render_state_lists_isa': driver.read_json(lifeos / 'MEMORY/STATE/isa-render-debounce' / (session + '.json'))['edited_isas'] == [str(isa)],
                  'checkpoint_commits': len(driver.git(repo, 'log', '--format=%s').splitlines()),
                  'checkpoint_records_criterion': checkpoint.exists() and driver.read_json(checkpoint)['committed_iscs'] == ['ISC-1'],
                  'atlas_sources': [r['source'] for r in driver.read_json_lines(home / driver.ATLAS_EVENTS)] if (home / driver.ATLAS_EVENTS).exists() else [],
                  'knowledge_warning': 'Knowledge note written off-schema' in result,
                  'complexity_lines': complexity['cumulative'], 'dependency_count': complexity['deps'],
                  'evaluation_debounce_preserved': driver.read_json(lifeos / 'MEMORY/OBSERVABILITY/config-eval-state.json')['last_fire'] == (home / 'eval-baseline.txt').read_text(),
                  'all_files_match': True, 'applied_files': len(applied), 'failed_files': len(plan) - len(applied),
                  'hook_calls': len(traces)}
        if side == 'native':
            result['knowledge_warning'] = any('Knowledge note written off-schema' in r['stdout'] for r in traces)
        expected = {'isa_closed': True, 'view_matches_content': True, 'registry_present': True,
                    'render_state_lists_isa': True, 'checkpoint_commits': 1 if partial else 2,
                    'checkpoint_records_criterion': not partial, 'atlas_sources': [] if partial else ['projects'],
                    'knowledge_warning': not partial, 'complexity_lines': 0 if partial else 250,
                    'dependency_count': 0 if partial else 1, 'evaluation_debounce_preserved': True,
                    'all_files_match': True, 'applied_files': 1 if partial else len(plan),
                    'failed_files': 1 if partial else 0, 'hook_calls': expected_calls}
        assert result == expected, (result, expected)
        driver.write_json(home / 'batch-result.json', result)
    finally:
        if side == 'hermes':
            unload_plugins()
        cleanup_all_environments()


def fixture(home, source, plugins, uid, gid, partial, side):
    home.mkdir(parents=True)
    root = home / '.claude'
    root.mkdir()
    shutil.copytree(source / 'hooks', root / 'hooks')
    shutil.copytree(source / 'LIFEOS/TOOLS', root / 'LIFEOS/TOOLS')
    project = home / 'project'
    project.mkdir()
    isa = root / 'LIFEOS/MEMORY/WORK/pair-run/ISA.md'
    isa.parent.mkdir(parents=True)
    started = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    initial = driver.ISA_SEED.format(started=started)
    plan = [{'path': str(isa), 'before': initial, 'edits': [{'old_string': '- [ ] ISC-1:', 'new_string': '- [x] ISC-1:'}]}]
    targets = [('locked/second.txt', 'old\n', [{'old_string': 'old', 'new_string': 'new'}])] if partial else [
        ('source.txt', 'old\nkeep\ntail\n', [{'old_string': 'old', 'new_string': '\n'.join(f'line {i}' for i in range(250))},
                                               {'old_string': 'tail', 'new_string': 'tail changed'}]),
        ('package.json', '{\n "dependencies": {\n }\n}\n', [{'old_string': ' "dependencies": {', 'new_string': ' "dependencies": {\n "fixture-dependency": "^1.0.0"'}]),
        ('PROJECTS.md', 'old\n', [{'old_string': 'old', 'new_string': 'new'}]),
        ('fixture.hook.ts', 'export const fixture = 0;\n', [{'old_string': 'export const fixture = 0;', 'new_string': 'export const fixture = 1;'}]),
        ('knowledge', 'old\n', [{'old_string': 'old', 'new_string': 'new'}])]
    for relative, before, edits in targets:
        path = (root / 'LIFEOS/MEMORY/KNOWLEDGE/Ideas/pair-idea.md') if relative == 'knowledge' else project / relative
        plan.append({'path': str(path), 'before': before, 'edits': edits})
    for item in plan:
        path = Path(item['path']); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(item['before'])
    repo = home / 'checkpoint-repo'
    repo.mkdir()
    (repo / 'tracked.txt').write_text('base\n')
    for command in (('init', '--quiet'), ('config', 'user.name', 'Fixture'), ('config', 'user.email', 'fixture@example.invalid'),
                    ('add', 'tracked.txt'), ('commit', '--quiet', '-m', 'Fixture base')):
        driver.git(repo, *command)
    (repo / 'tracked.txt').write_text('change\n')
    (root / 'checkpoint-repos.txt').write_text(str(repo) + '\n')
    driver.write_json(home / 'plan.json', plan)
    now = datetime.now(timezone.utc).isoformat()
    driver.write_json(root / 'LIFEOS/MEMORY/OBSERVABILITY/config-eval-state.json', {'last_fire': now})
    (home / 'eval-baseline.txt').write_text(now)
    hooks = [{'type': 'command', 'command': f'bun "$HOME/.claude/hooks/{program}.hook.ts"'} for program in PROGRAMS]
    driver.write_json(root / 'settings.json', {'hooks': {'PostToolUse': [{'matcher': 'Edit', 'hooks': hooks}]}})
    profile = home / '.hermes'
    profile.mkdir()
    (profile / 'plugins').symlink_to(plugins, target_is_directory=True)
    driver.write_json(profile / 'config.yaml', {'terminal': {'env_type': 'local'}, 'plugins': {'enabled': ['lifeos-hook-bridge']}})
    # Keep literal checkpoint commands so the bridge can suppress incomplete claims.
    shim = home / 'bin/bun'
    shim.parent.mkdir()
    shim.write_text('#!' + sys.executable + '\nimport base64,os,sys\nfrom pathlib import Path\n'
                   f'programs={PROGRAMS!r}\n'
                   'name=Path(sys.argv[1]).name.removesuffix(".hook.ts")\n'
                   'if name in programs:\n'
                   ' command=os.environ["PAIR_REAL_BUN"]+" "+__import__("shlex").quote(sys.argv[1])\n'
                   ' args=[sys.executable,os.environ["PAIR_TRACE"],"run",f"PostToolUse.10.{programs.index(name)+1}",'
                   'str(Path(os.environ["HOME"])/"hooks.jsonl"),base64.b64encode(command.encode()).decode()]\n'
                   ' os.execv(sys.executable,args)\n'
                   'os.execv(os.environ["PAIR_REAL_BUN"],[os.environ["PAIR_REAL_BUN"],*sys.argv[1:]])\n')
    shim.chmod(0o755)
    for path in (home, *home.rglob('*')):
        if not path.is_symlink():
            os.chown(path, uid, gid)
    if partial:
        (project / 'locked').chmod(0o555)
        (project / 'locked/second.txt').chmod(0o444)


def run(configuration, output):
    config = driver.read_json(configuration)
    output.mkdir()
    results = []
    for partial in (False, True):
        name = 'batch-partial' if partial else 'batch-success'
        case = {'id': name, 'native_cli_dispatch': False, 'hermes_tool_dispatch': True,
                'registrations': [f'PostToolUse.10.{number}' for number in range(1, 8)]}
        for side in ('native', 'hermes'):
            spec = config[side]
            uid, gid = config['hermes']['uid'], config['hermes']['gid']
            home = Path(config['hermes']['home_root']) / output.name / name / side
            fixture(home, Path(spec['hook_root']), Path(config['hermes']['plugins_path']), uid, gid, partial, side)
            environment = {**os.environ, **config['hermes'].get('environment', {}),
                           'HOME': str(home), 'HERMES_HOME': str(home / '.hermes'), 'CLAUDE_CONFIG_DIR': str(home / '.claude'),
                           'LIFEOS_DIR': str(home / '.claude/LIFEOS'), 'LIFEOS_CONFIG_DIR': str(home / '.claude'),
                           'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'), 'LIFEOS_NOTIFICATION_CHANNEL': 'discord',
                           'TERMINAL_CWD': str(home / 'project'), 'HERMES_WRITE_SAFE_ROOT': str(home),
                           'PAIR_REAL_BUN': str(Path(__file__).parent / 'bin/bun'), 'PAIR_TRACE': config['native']['trace_script']}
            shared_path = str(Path(__file__).parent / 'bin') + ':' + os.environ['PATH']
            environment['PATH'] = str(home / 'bin') + ':' + shared_path if side == 'hermes' else shared_path
            with (home / 'host.log').open('w') as log:
                result = subprocess.run([config['hermes']['command'][0], str(Path(__file__).resolve()), 'host', side,
                                         str(int(partial))], cwd=home / 'project', env=environment,
                                        user=uid, group=gid, extra_groups=[],
                                        stdout=log, stderr=subprocess.STDOUT, timeout=90)
            assert result.returncode == 0, (side, name, (home / 'host.log').read_text())
            case[side] = driver.read_json(home / 'batch-result.json')
        assert case['native'] == case['hermes'], case
        results.append(case)
        driver.write_json(output / 'batch-results.json', {'cases': results})
        print(json.dumps({'case': name, 'passed': True}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'host':
        run_host(sys.argv[2], bool(int(sys.argv[3])))
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('configuration', type=Path)
        parser.add_argument('output', type=Path)
        args = parser.parse_args()
        run(args.configuration, args.output)
