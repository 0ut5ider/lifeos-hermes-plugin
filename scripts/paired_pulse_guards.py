# ABOUTME: Runs native HTTP registrations against real Pulse daemons in paired CLI turns.
# ABOUTME: Records forwarded guard decisions without replacing their native implementation.

import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import threading
from urllib.request import Request, urlopen

import paired_lifecycle_effects as driver


CASES = ('generic-skill-pulse-block', 'generic-skill-pulse-allow', 'generic-agent-pulse-foreground')


def run(configuration, output, support):
    module = importlib.util.spec_from_file_location('pulse_fixture', support)
    fixtures = importlib.util.module_from_spec(module)
    module.loader.exec_module(fixtures)
    original_fixture = driver.make_fixture
    original_snapshot = driver.state_snapshot
    original_run_side = driver.run_side
    servers = []

    def make_fixture(home, case, source, trace):
        definitions = original_fixture(home, case, source, trace)
        pulse = fixtures.PulseFixture(home, source)
        servers.append(pulse)
        pulse.start()
        identifier = driver.CASES[case][0][0]
        guard = 'agent-guard' if case.startswith('generic-agent-') else 'skill-guard'
        program = source / 'LIFEOS/PULSE/modules/hooks.ts'

        class Trace(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                request = Request(f'http://127.0.0.1:{pulse.port}/hooks/{guard}', data=body,
                                  headers={'Content-Type': 'application/json'})
                with urlopen(request, timeout=5) as response:
                    returned = response.read()
                    status = response.status
                record = {'id': identifier, 'event': 'PreToolUse', 'stdin_base64': base64.b64encode(body).decode(),
                          'stdout': returned.decode(), 'stderr': '', 'exit_code': 0, 'http_status': status,
                          'native_program_sha256': hashlib.sha256(program.read_bytes()).hexdigest()}
                with (home / 'hooks.jsonl').open('a') as stream:
                    stream.write(json.dumps(record) + '\n')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(returned)))
                self.end_headers()
                self.wfile.write(returned)

            def log_message(self, *_):
                pass

        proxy = ThreadingHTTPServer(('127.0.0.1', 0), Trace)
        worker = threading.Thread(target=proxy.serve_forever, daemon=True)
        worker.start()
        servers.append(proxy)
        url = f'http://127.0.0.1:{proxy.server_port}/hooks/{guard}'
        settings_path = home / '.claude/settings.json'
        settings = json.loads(settings_path.read_text())
        settings['hooks']['PreToolUse'][-1]['hooks'] = [{'type': 'http', 'url': url, 'timeout': 5}]
        settings_path.write_text(json.dumps(settings))
        definitions[0] = {'id': identifier, 'command': url,
                          'source_files': {str(program): hashlib.sha256(program.read_bytes()).hexdigest()}}
        return definitions

    def state_snapshot(home, case, session_id='', *, after=False):
        if case not in CASES:
            return original_snapshot(home, case, session_id, after=after)
        if not after:
            return {'guard_calls': 0}
        traces = driver.read_json_lines(home / 'hooks.jsonl')
        outputs = []
        valid = len(traces) == 1
        for trace in traces:
            payload = json.loads(base64.b64decode(trace['stdin_base64']))
            specific = json.loads(trace['stdout']).get('hookSpecificOutput', {}) if trace['stdout'] else {}
            valid = valid and trace['http_status'] == 200 and payload['hook_event_name'] == 'PreToolUse'
            if case == 'generic-agent-pulse-foreground':
                valid = valid and payload['tool_name'] == 'Agent' and payload['tool_input'].get('run_in_background') is not True
                valid = valid and specific.get('permissionDecision') == 'allow'
                valid = valid and 'WARNING: Foreground agent' in specific.get('additionalContext', '')
                outputs.append('foreground-warning')
            else:
                valid = valid and payload['tool_name'] == 'Skill'
                valid = valid and payload['tool_input'].get('skill') == driver.GENERIC_CASES[case][2]
                blocked = case.endswith('-block')
                valid = valid and (specific.get('permissionDecision') == 'deny' if blocked else not specific)
                outputs.append('skill-denied' if blocked else '')
        return {'changed': {}, 'outputs': outputs, 'stderr_present': [False] * len(traces), 'guard_effect_valid': valid}

    driver.make_fixture = make_fixture
    driver.state_snapshot = state_snapshot

    def run_side(*args, **kwargs):
        first = len(servers)
        try:
            return original_run_side(*args, **kwargs)
        finally:
            for server in reversed(servers[first:]):
                if isinstance(server, ThreadingHTTPServer):
                    server.shutdown()
                    server.server_close()
                else:
                    server.stop()
            del servers[first:]

    driver.run_side = run_side
    try:
        return driver.run_controls(json.loads(configuration.read_text()), output, list(CASES))
    finally:
        for server in reversed(servers):
            if isinstance(server, ThreadingHTTPServer):
                server.shutdown()
                server.server_close()
            else:
                server.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run paired real Pulse guard cases')
    parser.add_argument('configuration', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--support', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'tests/test_native_pulse_guards.py')
    args = parser.parse_args()
    raise SystemExit(run(args.configuration, args.output, args.support))
