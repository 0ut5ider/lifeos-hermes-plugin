# ABOUTME: Runs actual private-model Hermes turns in the admitted development profile.
# ABOUTME: Keeps synthetic prompts, process outcomes, and native tool responses on disk.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

stage = Path.home() / 'releases/qualification-0.5.0'
profile = Path.home() / '.hermes'
os.umask(0o077)
installed = Path(json.loads((profile / 'lifeos-memory.json').read_bytes())['root'])
environment = {'HOME': str(installed.parent), 'HERMES_HOME': str(profile),
    'PATH': '/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'LANG': 'C.UTF-8', 'TZ': 'America/Toronto',
    'LIFEOS_DIR': str(installed / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(installed / 'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'PYTHONDONTWRITEBYTECODE': '1'}
prompts = [
    ('remember', 'This is an development-release acceptance test with synthetic data. '
        'Remember exactly "Synthetic daily acceptance verification code is STABLE-050-DEV-04EFE633." '
        'Use project category, project "release-0.5.0-qualification", title "Synthetic release acceptance", '
        'and request_id "stable-050-dev-04efe633". Use lifeos_memory_remember once. '
        'Do not ask clarification. Return the actual tool receipt as JSON.'),
    ('search', 'This is a separate development-release acceptance conversation. '
        'Use lifeos_memory_search once with query "STABLE-050-DEV-04EFE633" and limit 5. Do not add a project argument. '
        'Use lifeos_memory_search. Return the actual matched synthetic content and reference as JSON. '
        'Do not ask clarification or use previous chat history.'),
]
reports = []
for name, prompt in prompts:
    query = stage / ('release-owner-turn-' + name + '-query.txt')
    output = stage / ('release-owner-turn-' + name + '.txt')
    if query.exists() or output.exists():
        raise RuntimeError('The actual owner-turn evidence already exists')
    query.write_text(prompt + '\n')
    query.chmod(0o600)
    started = time.monotonic()
    with output.open('w') as stream:
        result = subprocess.run([str(Path.home() / '.local/bin/hermes'), 'chat', '-Q', '--query-file', str(query),
            '--format', 'stream-json', '--toolsets', 'memory', '--max-turns', '8', '--run-budget', '180'],
            env=environment, cwd=profile, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
    report = {'turn': name, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'synthetic_input_only': True, 'private_model_request': True,
        'development_synthetic_memory_written': name == 'remember', 'cli_output': str(output),
        'tool_effect_verified': False}
    reports.append(report)
    (stage / 'release-owner-turn-processes.json').write_text(json.dumps(reports, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    if result.returncode:
        raise RuntimeError('The actual admitted Hermes turn does not complete')
