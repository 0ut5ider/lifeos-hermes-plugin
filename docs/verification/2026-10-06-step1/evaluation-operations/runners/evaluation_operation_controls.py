# ABOUTME: Measures configuration evaluations after actual batch and concurrent Hermes file operations.
# ABOUTME: Keeps native handler controls distinct from native CLI dispatch and records real child inference.
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import paired_lifecycle_effects as driver
from paired_evaluation_effects import configure_evaluation, wait_evaluation, RESULTS, LOG, STATE, SUITE, TRIAL_OUTPUT
from paired_response_server import response_handler


def host(side, mode):
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from model_tools import handle_function_call
    from tools.file_tools import patch_tool, read_file_tool
    from tools.terminal_tool import cleanup_all_environments

    home = Path.home()
    files = sorted((home / 'project').glob('control-*.hook.ts'))
    task = 'evaluation-operations'
    for path in files:
        result = json.loads(read_file_tool(str(path), task_id=task))
        assert not result.get('error'), result
    if side == 'hermes':
        discover_plugins()

    def apply(paths):
        text = '*** Begin Patch\n' + ''.join('*** Update File: ' + str(path)
            + '\n-OLD\n+NEW\n' for path in paths) + '*** End Patch'
        args = {'mode': 'patch', 'patch': text}
        result = (handle_function_call('patch', args, task_id=task, session_id='evaluation-operations',
                                      tool_call_id=paths[0].name)
                  if side == 'hermes' else patch_tool(**args, task_id=task))
        value, _ = json.JSONDecoder().raw_decode(result)
        assert value['success'], result
        assert value['files_modified'] == [str(path) for path in paths], value
        (home / (paths[0].name + '.tool.json')).write_text(json.dumps({'arguments': args, 'result': result}))
        if side == 'native':
            for path in paths:
                payload = {'hook_event_name': 'PostToolUse', 'session_id': 'evaluation-operations',
                           'tool_name': 'MultiEdit' if mode == 'batch' else 'Edit',
                           'tool_input': {'file_path': str(path), 'edits': [{'old_string': 'OLD', 'new_string': 'NEW'}]},
                           'tool_response': {'success': True}, 'cwd': str(home / 'project')}
                command = json.loads((home / '.claude/settings.json').read_text())['hooks']['PostToolUse'][-1]['hooks'][0]['command']
                result = subprocess.run(command, shell=True, input=json.dumps(payload), text=True,
                                        capture_output=True, timeout=20)
                assert result.returncode == 0, result.stderr
        return True

    try:
        if mode == 'batch':
            apply(files)
        else:
            with ThreadPoolExecutor(max_workers=len(files)) as pool:
                assert all(pool.map(lambda path: apply([path]), files))
        wait_evaluation(home, 'evaluation-write-pass')
        root = home / '.claude'
        rows = driver.read_json_lines(root / LOG)
        runs = [row for row in rows if row.get('event') == 'run']
        latest = driver.read_json(root / RESULTS / SUITE / 'latest.json')
        detail = driver.read_json(root / RESULTS / SUITE / latest['run_id'] / 'run.json') if latest else None
        traces = driver.read_json_lines(home / 'hooks.jsonl')
        outcome = {
            'files_applied': sum(path.read_text().strip() == 'NEW' for path in files),
            'hook_calls': len(traces), 'hook_errors_absent': all(not row.get('stderr') for row in traces),
            'single_completed_run': len(runs) == 1, 'runner_lock_absent': not (root / RESULTS / '.config-eval.lock').exists(),
            'valid_fire_state': isinstance(driver.read_json(root / STATE).get('last_fire'), str),
            'passed': runs[0].get('passed') if len(runs) == 1 else None,
            'trial_output_matches': bool(detail) and detail['detail'][0]['trials'][0]['output'] == TRIAL_OUTPUT,
            'published_result_matches': bool(latest) and latest.get('passed') is True,
        }
        (home / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
        expected = {'files_applied': len(files), 'hook_calls': len(files), 'hook_errors_absent': True,
                    'single_completed_run': True, 'runner_lock_absent': True, 'valid_fire_state': True,
                    'passed': True, 'trial_output_matches': True, 'published_result_matches': True}
        assert outcome == expected, (outcome, expected)
    finally:
        if side == 'hermes':
            unload_plugins()
        cleanup_all_environments()


def run(configuration, output):
    config = driver.read_json(configuration)
    output.mkdir()
    server = ThreadingHTTPServer(('127.0.0.1', 0), response_handler(config['model_environment']))
    server.observed = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    records = []
    try:
        for mode in ('batch', 'concurrent'):
            record = {'id': 'evaluation-' + mode, 'native_cli_dispatch': False, 'hermes_tool_dispatch': True}
            for side in ('native', 'hermes'):
                spec = config[side]
                home = Path(config['hermes']['home_root']) / output.name / mode / side
                driver.make_fixture(home, 'evaluation-edit-pass', Path(spec['hook_root']), Path(spec['trace_script']))
                for index in range(2 if mode == 'batch' else 4):
                    (home / 'project' / f'control-{index}.hook.ts').write_text('OLD\n')
                environment = {**config['hermes']['environment'], 'HOME': str(home),
                    'HERMES_HOME': str(home / '.hermes'), 'LIFEOS_DIR': str(home / '.claude/LIFEOS'),
                    'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'), 'LIFEOS_NOTIFICATION_CHANNEL': 'headless',
                    'TERMINAL_CWD': str(home / 'project'), 'HERMES_WRITE_SAFE_ROOT': str(home),
                    'CLAUDE_CODE_MAX_RETRIES': '0', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
                    'DISABLE_TELEMETRY': '1', 'DISABLE_ERROR_REPORTING': '1'}
                profile = home / '.hermes'
                profile.mkdir()
                (profile / 'plugins').symlink_to(config['hermes']['plugins_path'], target_is_directory=True)
                driver.write_json(profile / 'config.yaml', {'plugins': {'enabled': ['lifeos-hook-bridge']},
                    'model': {'provider': 'custom', 'base_url': endpoint + '/v1', 'api_key': 'PAIR_EVAL',
                              'default': 'lifecycle-fixture', 'api_mode': 'chat_completions'}})
                identity = config['hermes']
                for path in (home, *home.rglob('*')):
                    if not path.is_symlink():
                        os.chown(path, identity['uid'], identity['gid'])
                configure_evaluation(home, side, {**spec, 'uid': identity['uid'], 'gid': identity['gid']},
                                     endpoint, environment)
                with (home / 'host.log').open('w') as log:
                    process = subprocess.run([config['hermes']['command'][0], str(Path(__file__).resolve()), 'host', side, mode],
                        env=environment, cwd=home / 'project', user=identity['uid'], group=identity['gid'], extra_groups=[],
                        stdout=log, stderr=subprocess.STDOUT, timeout=150)
                record[side] = driver.read_json(home / 'outcome.json') if (home / 'outcome.json').exists() else None
                record.setdefault('errors', []).extend([] if process.returncode == 0 else [side + ': ' + (home / 'host.log').read_text()])
            if record['native'] != record['hermes']:
                record['errors'].append('paired outcomes differ')
            records.append(record)
            driver.write_json(output / 'operation-results.json', {'cases': records})
            print(json.dumps(record), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        private = output / 'requests-private.json'
        with os.fdopen(os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(server.observed, stream, indent=2)
            stream.write('\n')
    return int(any(row['errors'] for row in records))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'host':
        host(sys.argv[2], sys.argv[3])
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('configuration', type=Path)
        parser.add_argument('output', type=Path)
        args = parser.parse_args()
        raise SystemExit(run(args.configuration, args.output))
