# ABOUTME: Repeats the PR review checks and rejects warnings from subprocess finalization.
# ABOUTME: Captures commands, tested identities, complete output, and explicit completion status.
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
out = Path(__file__).parent
package = Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4')
native = Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
label, *modules = sys.argv[1:]
environment = os.environ | {
    'PYTHONDONTWRITEBYTECODE': '1',
    'PYTHONPATH': f'{root}:{root / "tests"}:{package / "hermes"}',
    'LIFEOS_HERMES_SOURCE': str(package / 'hermes'),
    'LIFEOS_MEMORY_SOURCE': str(native),
    'LIFEOS_TAB_STATE_SOURCE': str(native),
    'LIFEOS_FRESH_SOURCE': str(package / 'lifeos'),
    'LIFEOS_HARVEST_CONTROL_SOURCE': '/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install',
}
command = ['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python',
           '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', *modules]
record = {'command': command, 'environment': {key: value for key, value in environment.items()
          if key.startswith('LIFEOS_') or key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')},
          'source_hashes': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in (root / 'lifeos_hook_bridge').rglob('*')
          if path.is_file() and '__pycache__' not in path.parts},
          'worker_test_sha256': hashlib.sha256((root / 'tests/test_fresh_store_worker.py').read_bytes()).hexdigest()}
started = time.monotonic()
result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True)
output = result.stdout + result.stderr
warnings = re.findall(r'^.*(?:Warning:|Exception ignored).*$', output, re.M)
record.update(unittest_exit_code=result.returncode, exit_code=1 if warnings else result.returncode,
              elapsed_seconds=time.monotonic() - started, warning_lines=warnings,
              stdout=result.stdout, stderr=result.stderr)
(out / (label + '.json')).write_text(json.dumps(record, indent=2) + '\n')
(out / (label + '.done')).write_text(str(record['exit_code']) + '\n')
print(json.dumps({'label': label, 'exit_code': record['exit_code'],
                  'unittest_exit_code': result.returncode, 'warning_lines': len(warnings)}))
sys.exit(record['exit_code'])
