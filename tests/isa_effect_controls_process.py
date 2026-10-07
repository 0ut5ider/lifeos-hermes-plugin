# ABOUTME: Measures applied ISA mutations, registry transitions, views, and real checkpoint commits.
# ABOUTME: Compares native hook execution with installed Hermes dispatch in disposable repositories.
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from hermes_cli import plugins
from model_tools import handle_function_call
from tools.file_tools import read_file_tool, write_file_tool
from tools.terminal_tool import cleanup_all_environments

home = Path.home()
root = home / '.claude'
source = Path(os.environ['PAIR_FILE_SOURCE'])
side = os.environ['PAIR_FILE_SIDE']
settings = Path(os.environ['LIFEOS_HOOK_SETTINGS'])
profile = Path(os.environ['HERMES_HOME'])
root.mkdir(exist_ok=True)
(root / 'hooks').symlink_to(source / 'hooks', target_is_directory=True)
shutil.copytree(source / 'LIFEOS/TOOLS', root / 'LIFEOS/TOOLS', ignore=shutil.ignore_patterns('node_modules'))
(root / 'LIFEOS/PULSE').symlink_to(source / 'LIFEOS/PULSE', target_is_directory=True)
(profile / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['lifeos-hook-bridge']}, 'terminal': {'env_type': 'local'}}))
settings.write_text('{"hooks":{}}')
if side == 'hermes':
    plugins._reset_plugin_managers_for_tests()
    plugins.discover_plugins()
rows = []


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def git(repo, *args):
    process = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    return process.stdout.strip()


def configure(programs):
    settings.write_text(json.dumps({'permissions': {'allow': ['Read', 'Write', 'Edit']}, 'hooks': {'PostToolUse': [
        {'matcher': 'Read|Write|Edit|MultiEdit', 'hooks': [{'type': 'command', 'command': 'bun ' + str(source / 'hooks' / (program + '.hook.ts'))} for program in programs]}]}}))


def operation(tool, path, content, session, programs):
    configure(programs)
    path.parent.mkdir(parents=True, exist_ok=True)
    if tool != 'Read' and path.exists():
        view_result = json.loads(read_file_tool(str(path), task_id=session))
        assert not view_result.get('error'), view_result
    args = {'path': str(path)} if tool == 'Read' else {'path': str(path), 'content': content}
    name = 'read_file' if tool == 'Read' else 'write_file'
    if side == 'hermes':
        result = handle_function_call(name, args, task_id=session, session_id=session, tool_call_id=session)
        value, end = json.JSONDecoder().raw_decode(result)
        assert not value.get('error'), value
        return result[end:].strip()
    result = read_file_tool(**args, task_id=session) if tool == 'Read' else write_file_tool(**args, task_id=session)
    value = json.loads(result)
    assert not value.get('error'), value
    contexts = []
    for program in programs:
        process = subprocess.run(['bun', str(source / 'hooks' / (program + '.hook.ts'))],
            input=json.dumps({'hook_event_name': 'PostToolUse', 'tool_name': tool, 'tool_input': {'file_path': str(path), 'content': content},
                              'tool_response': value, 'session_id': session, 'cwd': str(home)}),
            capture_output=True, text=True, timeout=25)
        assert process.returncode == 0, process.stderr
        if process.stdout.strip():
            contexts.append(json.loads(process.stdout).get('hookSpecificOutput', {}).get('additionalContext', ''))
    return '\n'.join(contexts)


def isa(phase='observe', extra='', checked=False):
    started = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    return f'---\ntitle: Fixture\nstarted: {started}\nphase: {phase}\nprogress: {int(checked)}/1\n---\n\n## Claims\n- [{"x" if checked else " "}] ISC-1: Verify fixture\n{extra}'


try:
    programs = ['ISASync', 'ISAStaleWriteGuard']
    for name, relative, slug in [('work', '.claude/LIFEOS/MEMORY/WORK/fixture/ISA.md', 'fixture'),
                                 ('skill', '.claude/skills/fixture/ISA.md', 'project-fixture'),
                                 ('outside', 'outside/ISA.md', 'project-outside')]:
        session = 'sync-' + name
        path = home / relative
        operation('Write', path, isa(), session, programs)
        registry = root / 'LIFEOS/MEMORY/STATE/work.json'
        state = read(registry)['sessions'][slug]
        assert state['phase'] == 'observe' and state['sessionUUID'] == session, state
        view = root / 'LIFEOS/MEMORY/STATE/isa-session-view' / (session + '.json')
        assert read(view)['views'][str(path)] == hashlib.sha256(path.read_bytes()).hexdigest()
        operation('Write', path, isa('build'), session, programs)
        assert read(registry)['sessions'][slug]['phase'] == 'build'
        operation('Write', path, isa('complete', checked=True), session, programs)
        assert read(registry)['sessions'][slug]['phase'] == 'complete'
        page = path.with_suffix('.html')
        deadline = time.monotonic() + 8
        while not page.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        if not page.exists():
            diagnostic = subprocess.run(['bun', str(root / 'LIFEOS/TOOLS/ISARender.ts'), str(path), '--no-refresh'],
                                        capture_output=True, text=True, timeout=15)
            raise AssertionError({'path': str(path), 'render_missing': True,
                                  'renderer_exit_code': diagnostic.returncode,
                                  'renderer_stdout': diagnostic.stdout, 'renderer_stderr': diagnostic.stderr})
        assert 'Fixture' in page.read_text(), (path, 'render content missing')
        complete = path.read_text()
        operation('Read', path, '', session + '-resumed', programs)
        assert path.read_text() == complete
        if name == 'work':
            assert read(registry)['sessions'][slug]['sessionUUID'] == session + '-resumed'
        # Retain the same frontmatter while applying an actual body change.
        operation('Write', path, complete + '\nNew follow-up\n', session + '-resumed', programs)
        state = read(registry)['sessions'][slug]
        assert state['phase'] == 'learn' and state['iteration'] == 2, state
        assert 'phase: learn' in path.read_text() and 'Auto-resumed' in path.read_text()
        recorded = read(root / 'LIFEOS/MEMORY/STATE/isa-session-view' / (session + '-resumed.json'))['views'][str(path)]
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        assert recorded == current_hash, {'side': side, 'file': str(path), 'recorded': recorded, 'actual': current_hash, 'before_resume': hashlib.sha256(complete.encode()).hexdigest(), 'submitted': hashlib.sha256((complete + '\nNew follow-up\n').encode()).hexdigest()}
        rows.append({'id': session, 'created': True, 'phase_change': True, 'completed': True, 'actual_html': True, 'read_retains_content': True, 'resumed_phase': state['phase'], 'iteration': state['iteration'], 'view_matches': True})

    allowed = home / 'admitted'
    excluded = home / 'excluded'
    for repo in (allowed, excluded):
        repo.mkdir()
        git(repo, 'init', '--quiet')
        git(repo, 'config', 'user.name', 'Fixture')
        git(repo, 'config', 'user.email', 'fixture@example.invalid')
        (repo / 'proof.txt').write_text('base\n')
        git(repo, 'add', 'proof.txt')
        git(repo, 'commit', '--quiet', '-m', 'Fixture base')
        (repo / 'proof.txt').write_text('change\n')
    excluded_head = git(excluded, 'rev-parse', 'HEAD')
    (root / 'checkpoint-repos.txt').write_text(str(allowed) + '\n')
    path = root / 'skills/checkpoint/ISA.md'
    session = 'checkpoint'
    operation('Write', path, isa(checked=True), session, ['CheckpointPerISC'])
    checkpoint = root / 'LIFEOS/MEMORY/STATE/checkpoints/skill-checkpoint.checkpoint-state.json'
    state = read(checkpoint)
    assert state['committed_iscs'] == ['ISC-1'], state
    first = git(allowed, 'rev-parse', 'HEAD')
    message = git(allowed, 'show', '-s', '--format=%B', first)
    assert 'ISC-1 (checkpoint): Verify fixture' in message, message
    assert git(allowed, 'show', first + ':proof.txt') == 'change'
    assert not (path.parent / '.checkpoint-state.json').exists()
    assert git(excluded, 'rev-parse', 'HEAD') == excluded_head
    operation('Write', path, path.read_text(), session, ['CheckpointPerISC'])
    assert git(allowed, 'rev-parse', 'HEAD') == first
    (allowed / 'proof.txt').write_text('next\n')
    operation('Write', path, path.read_text() + '\n- [x] ISC-2: Second identity\n- [x] ISC-3: Third identity\n', session, ['CheckpointPerISC'])
    state = read(checkpoint)
    assert state['committed_iscs'] == ['ISC-1', 'ISC-2', 'ISC-3'], state
    assert 'ISC-2 (checkpoint): Second identity' in git(allowed, 'show', '-s', '--format=%B', 'HEAD')
    assert git(allowed, 'rev-list', '--count', 'HEAD') == '3'
    rows.append({'id': session, 'retrievable': True, 'skill_sidecar_outside': True, 'excluded_repository_retained': True, 'repeat_no_commit': True, 'committed_iscs': state['committed_iscs'], 'commit_count': 3, 'multiple_closure_contract': 'The first criterion commits changes; subsequent criteria retain identity without an empty commit.'})
finally:
    if side == 'hermes':
        plugins.unload_plugins()
    cleanup_all_environments()
(home / 'isa-results.json').write_text(json.dumps({'cases': rows}, indent=2) + '\n')
