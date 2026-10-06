# ABOUTME: Records main, delegated, and nested model requests of real Hermes turns through a relay.
# ABOUTME: Points the profile model route at a loopback relay to private FlashNext and restores it afterwards.
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from paired_response_server import response_handler  # noqa: E402

UPSTREAM = 'http://192.168.8.90:42071'
import re
token = re.findall(r'^  api_key:\s*"?([^"\s]+)"?\s*$', (Path.home() / '.hermes/config.yaml').read_text(), re.M)
assert len(token) == 1, 'expected one model api_key'
environment_file = root / 'model.env'
descriptor = os.open(environment_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(descriptor, 'w') as stream:
    stream.write(f'ANTHROPIC_BASE_URL={UPSTREAM} ANTHROPIC_MODEL=flashnext-w4a16-fp8ple ANTHROPIC_AUTH_TOKEN={token[0]}\n')
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), response_handler(environment_file))
server.observed = []
threading.Thread(target=server.serve_forever, daemon=True).start()
relay = f'http://127.0.0.1:{server.server_port}/v1'
config = Path.home() / '.hermes/config.yaml'
original = config.read_text()
marker = f'base_url: "{UPSTREAM}/v1"'
assert original.count(marker) == 1, 'expected one FlashNext base_url'
SCENARIOS = {
    'main': ['chat', '-q', 'Reply with exactly READY. Do not use any tools.'],
    'delegated': ['chat', '-t', 'delegation', '-q',
                  'Call the delegate_task tool exactly once with goal "Reply with exactly READY." and model "opus". '
                  'Do not set any other field. Then reply with the child result.'],
}


def summary(row):
    body = row['body']
    messages = body.get('messages') or []
    system = next((m.get('content') for m in messages if m.get('role') == 'system'), '')
    system = system if isinstance(system, str) else json.dumps(system)
    tools = [tool.get('function', {}).get('name') for tool in body.get('tools') or [] if isinstance(tool, dict)]
    return {'path': row['path'], 'requested_model': body.get('model'), 'actual_model': row.get('actual_model'),
            'upstream_status': row.get('upstream_status'), 'reasoning_effort': body.get('reasoning_effort'),
            'reasoning': body.get('reasoning'), 'messages': len(messages), 'tool_count': len(tools),
            'has_delegate_tool': 'delegate_task' in tools, 'system_sha256': hashlib.sha256(system.encode()).hexdigest(),
            'system_start': system[:90]}


results = {}
try:
    config.write_text(original.replace(marker, f'base_url: "{relay}"', 1))
    for name, arguments in SCENARIOS.items():
        before = len(server.observed)
        completed = subprocess.run([str(Path.home() / '.local/bin/hermes'), *arguments], text=True,
                                   capture_output=True, timeout=900, cwd=Path.home())
        rows = server.observed[before:]
        private = root / f'{name}-requests-private.json'
        descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(rows, stream, indent=1, default=str)
        results[name] = {'exit_code': completed.returncode, 'stdout_tail': completed.stdout[-1500:],
                         'requests': [summary(row) for row in rows if row['path'].startswith('/v1/chat')]}
        (root / 'route-results.json').write_text(json.dumps(results, indent=1) + '\n')
        print(name, completed.returncode, len(results[name]['requests']), flush=True)
finally:
    config.write_text(original)
    server.shutdown()
    (root / 'run.done').write_text('done\n')
