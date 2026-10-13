# ABOUTME: Repeats final review controls and preserves exact command output.
# ABOUTME: Reuses a recorded archive fixture and selects no live guest code.
import json
import os
from pathlib import Path
import subprocess
out = Path(__file__).resolve().parent
repo = out.parents[2]
metadata = json.loads((repo / 'docs/agents/2026-10-13-pr18-final-review-2/commands.json').read_text())
results = []
for record in metadata['commands']:
    if record['purpose'] not in ('Selected release and real service controls', 'Retained fixture artifact and lease controls', 'UI components'):
        continue
    env = dict(os.environ, **record.get('environment', {}))
    name = 'primary-' + record['stdout']
    with (out / name).open('w') as stdout, (out / ('primary-' + record['stderr'])).open('w') as stderr:
        result = subprocess.run(record['command'], cwd=repo, env=env, stdout=stdout, stderr=stderr)
    results.append({'command': record['command'], 'environment': record.get('environment', {}), 'exit_code': result.returncode, 'stdout': name})
    if result.returncode:
        break
(out / 'primary-controls.json').write_text(json.dumps(results, indent=2) + '\n')
(out / 'primary-controls.done').write_text(str(max(value['exit_code'] for value in results)) + '\n')
