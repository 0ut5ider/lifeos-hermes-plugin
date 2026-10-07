# ABOUTME: Measures actual Hermes approval rejection, interruption, and unattended refusal.
# ABOUTME: Uses real private model requests and a disposable protected instruction target.
import argparse
import fcntl
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import termios
import threading
import time

import paired_lifecycle_effects as driver
from paired_response_server import response_handler


def interactive(command, environment, home, execution, mode):
    command = [arg for arg in command if arg not in ('--oneshot', '-Q')]
    position = command.index('--format')
    del command[position:position + 2]
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 45, 160, 0, 0))
    process = subprocess.Popen(command, env=environment, cwd=home / 'project', stdin=slave,
                               stdout=slave, stderr=slave, start_new_session=True, **execution)
    os.close(slave)
    terminal = bytearray()
    acted = ended = False
    acted_at = last_exit = 0
    deadline = time.monotonic() + 100
    try:
        while process.poll() is None and time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    terminal.extend(os.read(master, 65536))
                except OSError:
                    break
                (home / 'terminal.log').write_bytes(terminal)
            if b'\x1b[6n' in terminal[-100:]:
                os.write(master, b'\x1b[1;1R')
            if not acted and b'<write to CLAUDE.md>' in terminal:
                os.write(master, b'2' if mode == 'deny' else b'\x03')
                acted, acted_at = True, time.monotonic()
            event_path = home / 'fixture-events.jsonl'
            events = driver.read_json_lines(event_path) if event_path.is_file() else []
            resolved = (any(row['hook_event_name'] == 'Stop' for row in events) if mode == 'deny'
                        else acted and b'Interrupting agent' in terminal and time.monotonic() - acted_at > 3)
            if resolved and not ended:
                os.write(master, b'/quit\r')
                ended, last_exit = True, time.monotonic()
            elif ended and time.monotonic() - last_exit > 1:
                os.write(master, b'\r')
                last_exit = time.monotonic()
        if process.poll() is None:
            raise TimeoutError('The actual approval control did not finish')
        assert acted and ended, (mode, terminal[-2000:])
        return process.returncode
    finally:
        (home / 'terminal.log').write_bytes(terminal)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        os.close(master)


def run(configuration, output):
    config = driver.read_json(configuration)
    spec = config['hermes']
    output.mkdir()
    server = ThreadingHTTPServer(('127.0.0.1', 0), response_handler(config['model_environment']))
    server.observed = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    records = []
    try:
        for mode in ('deny', 'interrupt', 'unattended'):
            home = Path(spec['home_root']) / output.name / mode
            driver.make_fixture(home, 'evaluation-write-claude', Path(spec['hook_root']), Path(spec['trace_script']))
            settings = home / '.claude/settings.json'
            value = driver.read_json(settings)
            value['hooks'].pop('PostToolUse', None)
            settings.write_text(json.dumps(value))
            profile = home / '.hermes'
            profile.mkdir()
            (profile / 'plugins').symlink_to(spec['plugins_path'], target_is_directory=True)
            driver.write_json(profile / 'config.yaml', {'plugins': {'enabled': ['lifeos-hook-bridge']},
                'model': {'provider': 'custom', 'base_url': endpoint + '/v1', 'api_key': 'PAIR_APPROVAL',
                          'default': 'lifecycle-fixture', 'api_mode': 'chat_completions'},
                'auxiliary': {'title_generation': {'model_upgrade_enabled': False}}})
            target = home / 'project/CLAUDE.md'
            prompt = (f'Write the file at {target} with exactly PAIR_APPROVAL_CONTENT. Use the file writing tool once. '
                      'If the operation is rejected, do not retry it or use another tool. Then reply with exactly READY.')
            environment = {**spec['environment'], 'HOME': str(home), 'HERMES_HOME': str(profile),
                'LIFEOS_DIR': str(home / '.claude/LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(settings),
                'TERMINAL_CWD': str(home / 'project'), 'HERMES_WRITE_SAFE_ROOT': str(home / 'project'),
                'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'TERM': 'xterm-256color',
                'HERMES_EPHEMERAL_SYSTEM_PROMPT': prompt, 'CLAUDE_CODE_MAX_RETRIES': '0',
                'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'DISABLE_TELEMETRY': '1', 'DISABLE_ERROR_REPORTING': '1'}
            for path in (home, *home.rglob('*')):
                if not path.is_symlink():
                    os.chown(path, spec['uid'], spec['gid'])
            os.chown(home.parent, spec['uid'], spec['gid'])
            execution = {'user': spec['uid'], 'group': spec['gid'], 'extra_groups': []}
            command = [*spec['command'], prompt]
            command[command.index('-t') + 1] = 'file'
            before = len(server.observed)
            if mode == 'unattended':
                with (home / 'cli.log').open('w') as log:
                    process = subprocess.run(command, env=environment, cwd=home / 'project',
                                             stdout=log, stderr=subprocess.STDOUT, timeout=60, **execution)
                code = process.returncode
            else:
                code = interactive(command, environment, home, execution, mode)
            events = driver.read_json_lines(home / 'fixture-events.jsonl')
            requests = [row for row in server.observed[before:] if driver.conversation_request(row, 'approval-' + mode)]
            record = {'id': 'approval-' + mode, 'exit_code': code, 'target_absent': not target.exists(),
                      'session_end_count': sum(row['hook_event_name'] == 'SessionEnd' for row in events),
                      'stop_count': sum(row['hook_event_name'] == 'Stop' for row in events),
                      'model_requests': len(requests),
                      'model_responses_successful': all(row.get('upstream_status') == 200 for row in requests)}
            assert code == 0 and record['target_absent'] and record['session_end_count'] == 1, record
            assert requests and record['model_responses_successful'], record
            if mode != 'interrupt':
                assert record['stop_count'] == 1, record
                bodies = '\n'.join(json.dumps(row['body']) for row in requests)
                expected = 'denied' if mode == 'deny' else 'no interactive user or gateway'
                assert expected in bodies.lower(), record
            records.append(record)
            driver.write_json(output / 'approval-results.json', {'cases': records})
            print(json.dumps(record), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        private = output / 'requests-private.json'
        with os.fdopen(os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(server.observed, stream, indent=2)
            stream.write('\n')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.configuration, args.output))
