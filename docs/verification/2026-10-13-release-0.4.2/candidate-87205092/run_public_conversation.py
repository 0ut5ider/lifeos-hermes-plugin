# ABOUTME: Runs an actual Hermes request to prepare the latest published complete integration.
# ABOUTME: Keeps the native tool stream private and leaves installation approval to the dashboard owner.
import json
import os
from pathlib import Path
import subprocess
import time

stage = Path.home() / 'releases/qualification-0.4.2-87205092'
query = stage / 'public-conversation-query.txt'
output = stage / 'public-conversation-stream.txt'
assert not query.exists() and not output.exists(), 'The actual conversation evidence already exists'
query.write_text('This is an isolated synthetic release acceptance test. Prepare the latest stable complete LifeOS integration update for this Hermes profile. Use the terminal tool to run hermes lifeos-release prepare without a version argument. Use a 300 second command timeout. Do not apply the update. Do not change configuration, read memory, or send any message outside this conversation. Return the actual operation identifier and tool state. The dashboard owner will review and approve the prepared operation.\n')
query.chmod(0o600)
environment = dict(os.environ, HOME=str(Path.home()), HERMES_HOME=str(Path.home() / '.hermes'),
    PATH=str(Path.home() / '.local/bin') + ':' + os.defpath,
    PYTHONDONTWRITEBYTECODE='1', LANG='C.UTF-8', TZ='America/Toronto')
started = time.monotonic()
with output.open('w') as stream:
    result = subprocess.run([str(Path.home() / '.local/bin/hermes'), 'chat', '-Q', '--query-file', str(query),
        '--format', 'stream-json', '--toolsets', 'terminal', '--max-turns', '8', '--run-budget', '600'],
        env=environment, cwd=Path.home() / '.hermes', stdout=stream, stderr=subprocess.STDOUT, timeout=900)
report = {'exit_code': result.returncode, 'elapsed_seconds': round(time.monotonic() - started, 3),
    'actual_tool_effect_verified': False, 'synthetic_test_profile_only': True}
(stage / 'public-conversation-process.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
assert result.returncode == 0, 'The actual Hermes conversation fails'
