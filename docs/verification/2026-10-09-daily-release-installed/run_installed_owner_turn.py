# ABOUTME: Runs actual private-model Hermes turns in the isolated admitted owner profile.
# ABOUTME: Keeps synthetic prompts, process outcomes, and native tool responses on disk.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile = Path(prepared['profile'])
installed = Path(prepared['installed'])
environment = {'HOME': str(installed.parent), 'HERMES_HOME': str(profile),
    'PATH': str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'PYTHONPATH': str(stage / 'package/hermes'), 'LANG': 'C.UTF-8', 'TZ': 'America/Toronto',
    'LIFEOS_DIR': str(installed / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(installed / 'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'PYTHONDONTWRITEBYTECODE': '1'}
prompts = [
    ('remember', 'This is an isolated daily-release acceptance test with synthetic data. '
        'Remember exactly "Synthetic daily acceptance verification code is D252-TEXT-4109." '
        'Use project category, project "daily-release-acceptance", title "Synthetic release acceptance", '
        'and request_id "daily-installed-owner-turn-4109". Use lifeos_memory_remember once. '
        'Do not ask clarification. Return the actual tool receipt as JSON.'),
    ('search', 'This is a separate isolated daily-release acceptance conversation. '
        'Search LifeOS lasting memory for "D252-TEXT-4109" in project "daily-release-acceptance". '
        'Use lifeos_memory_search. Return the actual matched synthetic content and reference as JSON. '
        'Do not ask clarification or use previous chat history.'),
]
reports = []
for name, prompt in prompts:
    query = stage / ('owner-turn-' + name + '-query.txt')
    output = stage / ('owner-turn-' + name + '.txt')
    if query.exists() or output.exists():
        raise RuntimeError('The actual owner-turn evidence already exists')
    query.write_text(prompt + '\n')
    query.chmod(0o600)
    started = time.monotonic()
    with output.open('w') as stream:
        result = subprocess.run([str(stage / 'bin/hermes'), 'chat', '-Q', '--query-file', str(query),
            '--format', 'stream-json', '--toolsets', 'memory', '--max-turns', '8', '--run-budget', '180'],
            env=environment, cwd=profile, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
    report = {'turn': name, 'exit_code': result.returncode,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'synthetic_input_only': True, 'private_model_request': True,
        'live_profile_changed': False, 'cli_output': str(output),
        'tool_effect_verified': False}
    reports.append(report)
    (stage / 'owner-turn-processes.json').write_text(json.dumps(reports, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    if result.returncode:
        raise RuntimeError('The actual admitted Hermes turn does not complete')
