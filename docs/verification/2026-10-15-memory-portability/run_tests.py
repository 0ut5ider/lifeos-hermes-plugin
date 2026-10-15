# ABOUTME: Runs portability tests against the qualified native LifeOS and Hermes programs.
# ABOUTME: Saves actual test output and exit status without reading personal source records.
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('tests', nargs='+')
arguments = parser.parse_args()
folder = Path(__file__).resolve().parent
repo = folder.parents[2]
cache = Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014')
package = cache / 'packages/0.5.0-04efe633'
native = cache / 'candidate-fixture-04efe633/account/.hermes/.lifeos-releases/6118299dea37462094bcb7d411effb73/reference-home/.claude'
python = '/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python'
assert (native / 'LIFEOS/TOOLS/MemorySystem.ts').is_file()
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TZ='UTC',
    PYTHONPATH=os.pathsep.join(map(str, (repo, repo / 'tests', package / 'hermes'))),
    LIFEOS_MEMORY_SOURCE=str(native), LIFEOS_HERMES_SOURCE=str(package / 'hermes'))
command = [python, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', *arguments.tests]
started = time.monotonic()
with (folder / (arguments.label + '.stdout')).open('w') as stdout, (folder / (arguments.label + '.stderr')).open('w') as stderr:
    result = subprocess.run(command, cwd=repo, env=environment, stdout=stdout, stderr=stderr, timeout=7200)
receipt = {'command': command, 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - started,
    'native_source': str(native), 'hermes_source': str(package / 'hermes'), 'daily_changed': False}
(folder / (arguments.label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
(folder / (arguments.label + '.done')).write_text(str(result.returncode) + '\n')
print(json.dumps(receipt))
raise SystemExit(result.returncode)
