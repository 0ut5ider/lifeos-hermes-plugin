# ABOUTME: Runs selected unittest modules in a disposable source copy with copied native fixtures.
# ABOUTME: Writes the full output and a JSON receipt with command, environment paths, exit code, and counts.
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

scratch = Path('/home/outsider/.cache/pr38-review-r1-scratch')
python = Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python')
tool_bin = '/home/outsider/.cache/lifeos-pulse-editor-20261014/tool-bin'
label, source, output, *modules = sys.argv[1:]
source, output = Path(source), Path(output)
native = scratch / 'native-claude'
environment = dict(os.environ, TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
    PATH=tool_bin + os.pathsep + os.environ['PATH'],
    PYTHONPATH=os.pathsep.join(map(str, (source, source / 'tests', scratch / 'hermes'))),
    LIFEOS_HERMES_SOURCE=str(scratch / 'hermes'), LIFEOS_MEMORY_SOURCE=str(native),
    LIFEOS_TASK_HOOK_PATH=str(native / 'hooks/TaskGovernance.hook.ts'), LIFEOS_FRESH_SOURCE=str(scratch / 'lifeos'),
    LIFEOS_TAB_STATE_SOURCE=str(native), LIFEOS_HARVEST_CONTROL_SOURCE=str(scratch / 'control-lifeos-install'),
    LIFEOS_FRESHNESS_CONTROL_SOURCE=str(scratch / 'control-lifeos-install'),
    LIFEOS_HERMES_REBUILD_SOURCE=str(scratch / 'hermes'), LIFEOS_MANAGED_REFERENCE=str(native),
    LIFEOS_TEST_PYTHON=str(python), PYTHON=str(python))
command = [str(python), '-B', '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', *modules]
started = time.time()
with open(output, 'w') as handle:
    result = subprocess.run(command, cwd=source, env=environment, stdout=handle, stderr=subprocess.STDOUT, timeout=3000)
text = output.read_text()
summary = re.findall(r'^(Ran \d+ tests.*|OK.*|FAILED.*)$', text, re.M)
cases = {kind: re.findall(r'^(\S+) \(([^)]+)\) \.\.\. ' + kind, text, re.M) for kind in ('FAIL', 'ERROR', 'skipped')}
print(json.dumps({'label': label, 'command': command, 'cwd': str(source),
    'environment': {k: v for k, v in environment.items() if k.startswith(('LIFEOS_', 'PYTHON', 'TZ'))},
    'exit': result.returncode, 'elapsed_seconds': round(time.time() - started, 1), 'summary': summary,
    'failures': cases['FAIL'], 'errors': cases['ERROR'], 'skipped': cases['skipped']}, indent=1))
