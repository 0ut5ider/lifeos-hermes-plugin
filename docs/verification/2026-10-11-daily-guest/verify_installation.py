# ABOUTME: Checks daily installed bytes, private services, and an actual private model conversation.
# ABOUTME: Records current installation gates without enabling lasting memory or Discord.
from contextlib import closing
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
import http.cookiejar

home = Path('/home/lifeos-hermes')
evidence = home / 'deployment/2026-10-11'
installation = json.loads((evidence / 'installation.json').read_text())
root = Path(installation['installed'])
profile = Path(installation['profile'])
package = home / 'releases/0.2.0-11577ed4'
runtime = home / 'runtime/hermes'
os.umask(0o077)
environment = json.loads((evidence / 'environment.json').read_text())
os.environ.update(environment, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
    DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
sys.path[:0] = [str(profile / 'plugins'), str(runtime)]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
candidate = json.loads((package / 'DAILY-CANDIDATE.json').read_text())
for relative, digest in candidate['plugin_files'].items():
    assert sha(profile / 'plugins/lifeos-hook-bridge' / Path(relative).relative_to('lifeos_hook_bridge')) == digest, relative
hermes_files = {}
for path in (package / 'hermes').rglob('*'):
    relative = path.relative_to(package / 'hermes')
    if '.git' in relative.parts or not path.is_file():
        continue
    hermes_files[str(relative)] = sha(path)
    assert sha(runtime / relative) == sha(path), str(relative)
native_files = {}
for path in (package / 'lifeos/LifeOS/install/LIFEOS').rglob('*'):
    relative = path.relative_to(package / 'lifeos/LifeOS/install')
    if {'USER', 'MEMORY', 'node_modules', '__pycache__'} & set(relative.parts) or not path.is_file():
        continue
    if str(relative) == 'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md':
        continue
    native_files[str(relative)] = sha(path)
    assert sha(root / relative) == sha(path), str(relative)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
assert not configuration.load()['ownership_enabled'] and not configuration.load()['sharing_enabled']
assert 'DISCORD_BOT_TOKEN' not in (profile / '.env').read_text()
assert sha(root / 'LIFEOS/USER/CONFIG/PULSE.user.toml') == sha(package / 'docs/deployment/daily-text/PULSE.user.toml')
assert subprocess.check_output(['timedatectl', 'show', '-p', 'Timezone', '--value'], text=True).strip() == 'America/Toronto'
credentials = json.loads((home / 'install-input/dashboard-access.json').read_text())
client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def request(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    response = client.open(urllib.request.Request('http://127.0.0.1:18819' + path, data=payload,
        headers={'Content-Type': 'application/json'} if payload is not None else {}), timeout=30)
    with response:
        return response.status, response.read()
anonymous_status = None
try:
    request('/api/plugins/lifeos-hook-bridge/memory')
except urllib.error.HTTPError as error:
    anonymous_status = error.code
assert anonymous_status == 401, anonymous_status
assert request('/auth/password-login', {'provider': 'basic', **credentials})[0] == 200
authenticated = request('/api/dashboard/plugins')
assert authenticated[0] == 200 and b'lifeos-hook-bridge' in authenticated[1]
assert request('/api/plugins/lifeos-hook-bridge/memory')[0] == 200
process = subprocess.run([str(home / '.local/bin/hermes'), 'config', 'check'],
    env=dict(os.environ), capture_output=True, text=True, timeout=60)
(evidence / 'config-check.txt').write_text(process.stdout + process.stderr)
assert process.returncode == 0, process.stdout + process.stderr
prompt = evidence / 'model-query.txt'
prompt.write_text('Installation acceptance D253-INSTALL. Reply exactly D253-INSTALL-PASS. Do not use tools.\n')
with (evidence / 'model-turn.jsonl').open('w') as output:
    result = subprocess.run([str(home / '.local/bin/hermes'), 'chat', '-Q', '--query-file', str(prompt),
        '--format', 'stream-json', '--max-turns', '4', '--run-budget', '120'],
        env=dict(os.environ), cwd=profile, stdout=output, stderr=subprocess.STDOUT, timeout=180)
assert result.returncode == 0
records = [json.loads(line) for line in (evidence / 'model-turn.jsonl').read_text().splitlines() if line.startswith('{')]
assert not any(row['type'] == 'tool_use' for row in records), records
assert any(row['type'] == 'result' and row.get('exit_code') == 0 for row in records), records
assert 'D253-INSTALL-PASS' in (evidence / 'model-turn.jsonl').read_text()
memory = module('memory_access').NativeMemory(root)
with memory._transaction() as connection:
    assert connection.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0] == 0
for database in (memory.database, root.parent / '.local/state/lifeos/atlas/atlas.db', profile / 'state.db'):
    if database.exists():
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
report = {'status': 'PASS', 'plugin_files': len(candidate['plugin_files']),
    'hermes_source_files': len(hermes_files), 'native_program_files': len(native_files),
    'anonymous_dashboard_status': anonymous_status, 'authenticated_dashboard_status': authenticated[0],
    'actual_hermes_private_model_turn': True, 'tool_calls': 0, 'active_facts_after_turn': 0,
    'ownership_enabled': False, 'sharing_enabled': False, 'discord_credentials_present': False,
    'python_version': sys.version, 'bun_version': subprocess.check_output(['bun', '--version'], text=True).strip(),
    'dependencies': sorted({(x.metadata['Name'], x.version) for x in importlib.metadata.distributions()}),
    'hermes_program_hashes': hermes_files, 'native_program_hashes': native_files}
(evidence / 'installation-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ('status', 'plugin_files', 'hermes_source_files',
    'native_program_files', 'actual_hermes_private_model_turn', 'active_facts_after_turn')}, indent=2))
