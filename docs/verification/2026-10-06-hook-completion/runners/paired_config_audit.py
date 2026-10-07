# ABOUTME: Compares configuration auditing in an interactive native session and idle Hermes bridge.
# ABOUTME: Changes synthetic settings and skills externally and rejects duplicate audit rows.

import argparse
import json
import os
from pathlib import Path
import pty
import select
import shlex
import signal
import subprocess
import sys
import time


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def run_side(side, spec, output):
    home = Path(spec['home_root']) / output.name / 'config-audit'
    root = home / '.claude'
    project = home / 'project'
    project.mkdir(parents=True)
    subprocess.run(['git', 'init', '--quiet', str(project)], check=True)
    host = Path(__file__).with_name('config_audit_fixture_host.py')
    command = f'{shlex.quote(sys.executable)} {shlex.quote(str(host))} trace'
    settings = {'env': {'PAIR_CFG': 'zero'}, 'hooks': {event: [{'hooks': [
        {'type': 'command', 'command': command}]}] for event in ('SessionStart', 'SessionEnd', 'ConfigChange')}}
    write(root / 'settings.json', settings)
    write(root / 'LIFEOS/MEMORY/STATE/pai-settings-snapshot.json', settings)
    write(root / '.claude.json', {'hasCompletedOnboarding': True,
          'projects': {str(project): {'hasTrustDialogAccepted': True}}})
    for name in ('settings.json', 'settings.local.json'):
        write(project / '.claude' / name, {'env': {'PAIR_PROJECT': 'zero'}})
    skill = root / 'skills/fixture-config/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('---\nname: fixture-config\ndescription: Synthetic config fixture\n---\nFixture text.\n')
    write(home / '.hermes/config.yaml', {'skills': {'trusted_project_dirs': [str(project)]}, 'terminal': {'env_type': 'local'}})
    for path in (home, *home.rglob('*')):
        os.chown(path, spec['uid'], spec['gid'])
    environment = {**os.environ, **spec.get('environment', {}), 'HOME': str(home), 'HERMES_HOME': str(home / '.hermes'),
        'CLAUDE_CONFIG_DIR': str(root), 'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_CONFIG_DIR': str(root),
        'LIFEOS_NOTIFICATION_CHANNEL': 'discord', 'TERMINAL_CWD': str(project), 'TERM': 'xterm-256color',
        'PAIR_NATIVE_PROGRAM': str(Path(spec['hook_root']) / 'hooks/EventLogger.hook.ts'),
        'ANTHROPIC_BASE_URL': 'http://127.0.0.1:1', 'ANTHROPIC_AUTH_TOKEN': 'CONFIG_FIXTURE',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'DISABLE_TELEMETRY': '1', 'DISABLE_ERROR_REPORTING': '1'}
    execution = {'user': spec['uid'], 'group': spec['gid'], 'extra_groups': []}
    master = None
    terminal = bytearray()
    if side == 'native':
        master, slave = pty.openpty()
        cli = [spec['command'][0], '--model', 'lifecycle-fixture']
        process = subprocess.Popen(cli, env=environment, cwd=project, stdin=slave, stdout=slave, stderr=slave,
                                   start_new_session=True, **execution)
        os.close(slave)
    else:
        environment['PYTHONPATH'] = str(Path(__file__).parent) + ':' + environment['PYTHONPATH']
        log = (home / 'bridge.log').open('w')
        process = subprocess.Popen([spec['command'][0], str(host), 'bridge'], env=environment, cwd=project,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True, **execution)
    last_enter = 0

    def pump():
        nonlocal last_enter
        if master is not None and select.select([master], [], [], 0.1)[0]:
            try:
                terminal.extend(os.read(master, 65536))
            except OSError:
                pass
        if process.poll() is not None:
            raise RuntimeError(f'{side} watcher exited with {process.returncode}')
        if master is not None and not native_ready() and time.monotonic() - last_enter > 2:
            os.write(master, b'\r')
            last_enter = time.monotonic()
        time.sleep(0.1)

    def native_ready():
        return b'for shortcuts' in terminal or b'manual mode on' in terminal

    def await_count(count, timeout=25):
        deadline = time.monotonic() + timeout
        while len(rows(home / 'hooks.jsonl')) < count and time.monotonic() < deadline:
            pump()
        if len(rows(home / 'hooks.jsonl')) != count:
            raise AssertionError(f'{side}: expected {count} configuration events, got {len(rows(home / "hooks.jsonl"))}')

    try:
        deadline = time.monotonic() + 40
        while (not rows(home / 'events.jsonl') or side == 'native' and not native_ready()) and time.monotonic() < deadline:
            pump()
        assert rows(home / 'events.jsonl'), f'{side} session did not start'
        assert side != 'native' or native_ready(), 'The native interactive prompt did not become ready'
        # SessionStart precedes onboarding dialogs and watcher initialization.
        finish = time.monotonic() + 2
        while time.monotonic() < finish:
            pump()
        changes = [('user-one', 'user_settings', root / 'settings.json'),
                   ('user-two', 'user_settings', root / 'settings.json'),
                   ('project', 'project_settings', project / '.claude/settings.json'),
                   ('project-two', 'project_settings', project / '.claude/settings.json'),
                   ('local', 'local_settings', project / '.claude/settings.local.json'),
                   ('local-two', 'local_settings', project / '.claude/settings.local.json'),
                   ('skill', 'skills', skill), ('skill-two', 'skills', skill)]
        measured = []
        for index, (name, source, path) in enumerate(changes, 1):
            if source == 'skills':
                path.write_text(path.read_text() + 'Additional fixture text.\n')
            else:
                value = json.loads(path.read_text())
                value['env'] = {'PAIR_CFG' if source == 'user_settings' else 'PAIR_PROJECT': name}
                write(path, value)
            await_count(index)
            finish = time.monotonic() + 2
            while time.monotonic() < finish:
                pump()
            traces = rows(home / 'hooks.jsonl')
            assert len(traces) == index, (side, name, 'duplicate change')
            trace = traces[-1]
            payload = trace['payload']
            assert payload['source'] == source and payload.get('file_path') == str(path), payload
            audits = rows(root / 'LIFEOS/MEMORY/OBSERVABILITY/config-changes.jsonl')
            assert len(audits) == index and audits[-1]['session_id'] == payload['session_id']
            assert trace['exit_code'] == 0 and not trace['stdout'] and '[ConfigAudit] Logged:' in trace['stderr']
            row = audits[-1]
            assert row['source'] == source and row['config_path'] == str(path), row
            expected_key = ('env' if source == 'user_settings' or name.endswith('-two') and source != 'skills'
                            else 'content' if name == 'skill-two' else 'initial')
            assert row['config_key'] == expected_key, row
            measured.append({'id': name, 'source': source, 'file_path': str(path.relative_to(home)),
                             'config_key': row['config_key'], 'change_summary': row['change_summary'],
                             'native_audit_path': row['config_path'].replace(str(home), '<home>')})
        return {'changes': measured, 'hook_calls': len(measured), 'duplicate_rows': 0}
    finally:
        if side == 'hermes':
            (home / 'finish').touch()
            process.wait(timeout=10)
            log.close()
        elif process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        if master is not None:
            os.close(master)
            (home / 'terminal.log').write_bytes(terminal)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    config = json.loads(args.configuration.read_text())
    result = {}
    for side in ('native', 'hermes'):
        result[side] = run_side(side, config[side], args.output)
        write(args.output / 'config-results.json', result)
    assert result['native'] == result['hermes'], result
    print(json.dumps(result, indent=2))
