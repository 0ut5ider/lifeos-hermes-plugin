# ABOUTME: Observes manual native writers in a disposable managed owner fixture.
# ABOUTME: Records synthetic effects and exact program hashes without changing installed data.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from test_memory_pulse_auth import MemoryPulseAuthTests
from test_memory_native import SOURCE

fixture = MemoryPulseAuthTests()
try:
    fixture.setUp()
    root = fixture.fixture.fixture.root
    home = fixture.home
    directory = root / 'LIFEOS/USER/TELOS/CURRENT_STATE'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'ACTIVITY.md'
    target.write_text('# Activity\n')
    identity = root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
    identity.write_text('---\npreferences:\n  temperature_unit: SyntheticManualUnit\n---\n')
    environment = dict(os.environ, HOME=str(home), LIFEOS_DIR=str(root / 'LIFEOS'),
                       LIFEOS_CONFIG_DIR=str(root / 'LIFEOS/USER/CONFIG'))
    for key in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
        environment.pop(key, None)
    observations = []
    tools = SOURCE / 'LIFEOS/TOOLS'
    def run(name, arguments):
        program = tools / name
        result = subprocess.run(['bun', '--no-install', str(program), *arguments],
                                capture_output=True, text=True, timeout=30, env=environment, cwd=home)
        observations.append({'program': name, 'sha256': hashlib.sha256(program.read_bytes()).hexdigest(),
            'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
            'managed_connector_present': (root / 'LIFEOS/USER/CONFIG/memory-access.json').is_file(),
            'current_owner_context_present': 'LIFEOS_MEMORY_CONTEXT' in environment})
        return result
    run('ProposeCurrentStateEntry.ts', ['--source', 'manual', '--target', 'ACTIVITY',
                                     '--json', '{"name":"SyntheticManualProposal"}'])
    queue = directory / 'proposals.jsonl'
    observations[-1]['queue_created'] = queue.exists()
    proposal = json.loads(queue.read_text().splitlines()[0]) if queue.exists() else None
    run('ApproveCurrentStateEntries.ts', ['--review'])
    observations[-1]['synthetic_payload_disclosed'] = 'SyntheticManualProposal' in observations[-1]['stdout']
    if proposal is not None:
        run('ApproveCurrentStateEntries.ts', ['--approve', proposal['id']])
        observations[-1]['target_published'] = 'SyntheticManualProposal' in target.read_text()
    run('SyncIdentityToSettings.ts', [])
    observations[-1]['settings_published'] = 'SyntheticManualUnit' in (root / 'settings.json').read_text()
    print(json.dumps({'source': str(SOURCE), 'observations': observations}, indent=2))
finally:
    fixture.doCleanups()
