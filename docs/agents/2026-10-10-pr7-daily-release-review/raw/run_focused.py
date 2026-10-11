# ABOUTME: Runs independent PR7 review checks without changing release evidence.
# ABOUTME: Keeps commands, process output, source hashes, and completion markers on disk.
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
out = Path(__file__).parent
package = Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4')
native = Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
environment = os.environ | {
    'PYTHONDONTWRITEBYTECODE': '1',
    'PYTHONPATH': f'{root}:{root / "tests"}:{package / "hermes"}',
    'LIFEOS_HERMES_SOURCE': str(package / 'hermes'),
    'LIFEOS_MEMORY_SOURCE': str(native),
    'LIFEOS_TAB_STATE_SOURCE': str(native),
    'LIFEOS_FRESH_SOURCE': str(package / 'lifeos'),
    'LIFEOS_HARVEST_CONTROL_SOURCE': '/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install',
}
command = [
    '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python',
    '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
    'test_fresh_store', 'test_memory_http', 'test_memory_algorithm_jobs',
]
record = {
    'command': command, 'environment': {key: environment[key] for key in environment if key.startswith('LIFEOS_') or key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')},
    'source_hashes': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / 'lifeos_hook_bridge').rglob('*') if p.is_file() and '__pycache__' not in p.parts},
}
started = time.monotonic()
with (out / 'focused.stdout').open('w') as stdout, (out / 'focused.stderr').open('w') as stderr:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stdout, stderr=stderr)
record.update(exit_code=result.returncode, elapsed_seconds=time.monotonic() - started)
(out / 'focused.json').write_text(json.dumps(record, indent=2) + '\n')
(out / 'focused.done').write_text(str(result.returncode) + '\n')
