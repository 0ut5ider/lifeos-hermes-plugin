# ABOUTME: Verifies an applied Hermes batch patch delivers the actual knowledge warning to the model.
# ABOUTME: Uses private inference and retains wire hashes while keeping full requests private.
import argparse
import base64
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading

import paired_lifecycle_effects as driver
from paired_response_server import response_handler


def run(configuration, output):
    config = driver.read_json(configuration)
    spec = config['hermes']
    output.mkdir()
    home = Path(spec['home_root']) / output.name / 'knowledge-batch'
    definitions = driver.make_fixture(home, 'knowledge-edit-off-schema', Path(spec['hook_root']),
                                      Path(spec['trace_script']))
    target = driver.project_dir(home, 'knowledge-edit-off-schema') / 'pair-idea.md'
    server = ThreadingHTTPServer(('127.0.0.1', 0), response_handler(config['model_environment']))
    server.observed = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    profile = home / '.hermes'
    profile.mkdir()
    (profile / 'plugins').symlink_to(spec['plugins_path'], target_is_directory=True)
    prompt = (f'Read {target} once. Then use the patch tool with mode "patch" and this exact patch. '
              'Do not use mode "replace" or the write_file tool. Do not change any other text. '
              'After the patch, reply with exactly READY.\n'
              '*** Begin Patch\n*** Update File: ' + str(target)
              + '\n-PAIR_OLD_LINE\n+PAIR_NEW_LINE\n*** End Patch')
    driver.write_json(profile / 'config.yaml', {'plugins': {'enabled': ['lifeos-hook-bridge']},
        'file_tools': {'patch_format': 'v4a'},
        'model': {'provider': 'custom', 'base_url': f'http://127.0.0.1:{server.server_port}/v1',
                  'api_key': 'PAIR_KNOWLEDGE', 'default': 'lifecycle-fixture', 'api_mode': 'chat_completions'},
        'auxiliary': {'title_generation': {'model_upgrade_enabled': False}}})
    env = {**spec['environment'], 'HOME': str(home), 'HERMES_HOME': str(profile),
           'LIFEOS_DIR': str(home / '.claude/LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(home / '.claude/settings.json'),
           'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'TERMINAL_CWD': str(target.parent),
           'HERMES_WRITE_SAFE_ROOT': str(target.parent), 'HERMES_EPHEMERAL_SYSTEM_PROMPT': prompt}
    for path in (home, *home.rglob('*')):
        if not path.is_symlink():
            os.chown(path, spec['uid'], spec['gid'])
    os.chown(home.parent, spec['uid'], spec['gid'])
    command = [*spec['command'], prompt]
    command[command.index('-t') + 1] = 'file'
    try:
        with (home / 'cli.log').open('w') as log:
            result = subprocess.run(command, env=env, cwd=target.parent,
                user=spec['uid'], group=spec['gid'], extra_groups=[], timeout=90,
                stdout=log, stderr=subprocess.STDOUT)
        requests = [row for row in server.observed if driver.conversation_request(row, 'knowledge-batch')]
        assert result.returncode == 0 and requests, (result.returncode, len(requests))
        assert all(row.get('upstream_status') == 200 for row in requests), [row.get('upstream_status') for row in requests]
        calls = []
        for row in requests:
            body = json.loads(base64.b64decode(row['response_body_base64']))
            for choice in body.get('choices', []):
                calls.extend(choice.get('message', {}).get('tool_calls', []))
        patches = [json.loads(call['function']['arguments']) for call in calls
                   if call.get('function', {}).get('name') == 'patch']
        assert len(patches) == 1 and patches[0].get('mode') == 'patch', patches
        assert target.read_text().strip() == driver.FILE_SEED.replace('PAIR_OLD_LINE', 'PAIR_NEW_LINE').strip()
        contexts = []
        for trace in driver.read_json_lines(home / 'hooks.jsonl'):
            assert trace['exit_code'] == 0 and not trace['stderr'], trace
            contexts.append(json.loads(trace['stdout'])['hookSpecificOutput']['additionalContext'])
        assert len(contexts) == 1 and contexts[0].startswith(driver.KNOWLEDGE_WARNING), contexts
        assert any(contexts[0] in json.dumps(row['body'], ensure_ascii=False) or
                   any(contexts[0] in str(message.get('content', '')) for message in row['body'].get('messages', []))
                   for row in requests), 'The actual warning is absent from the next model request'
        cli_results = []
        for line in (home / 'cli.log').read_text().splitlines():
            if line.startswith('{'):
                row = json.loads(line)
                if row.get('type') == 'result':
                    cli_results.append(row)
        assert len(cli_results) == 1 and cli_results[0].get('text', '').strip() == 'READY', cli_results
        proof = []
        for row in requests:
            for field in ('body', 'response_body'):
                assert hashlib.sha256(base64.b64decode(row[field + '_base64'])).hexdigest() == row[field + '_sha256']
            proof.append({key: row[key] for key in ('path', 'body_sha256', 'response_body_sha256',
                                                    'upstream_status', 'actual_model')})
        driver.write_json(output / 'wire-proof.json', proof)
        driver.write_json(output / 'result.json', {'native_cli_dispatch': False, 'hermes_tool_dispatch': True,
            'patch_mode': 'patch', 'files_applied': 1, 'hook_calls': 1, 'actual_warning_delivered': True,
            'actual_response_delivered': True, 'model_requests': len(requests), 'home': str(home),
            'hook_definitions': definitions, 'patch_arguments': patches})
        return 0
    finally:
        server.shutdown()
        server.server_close()
        with os.fdopen(os.open(output / 'requests-private.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(server.observed, stream)
            stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.configuration, args.output))
