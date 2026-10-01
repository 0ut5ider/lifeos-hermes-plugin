# ABOUTME: Verifies all memory cases and the neighboring host and patch contracts.
# ABOUTME: Records each command, complete output, and a final exit marker on disk.
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
output = Path(__file__).resolve().parent
commands = [
    [sys.executable, '-m', 'unittest', 'discover', '-v', '-s', 'tests', '-p', 'test_memory*.py'],
    [sys.executable, '-m', 'unittest', '-v', 'test_hermes_memory_provider', 'test_prepare_sources', 'test_patch_bundle'],
]
status = 0
with (output / 'regression.txt').open('w') as stream:
    stream.write('Source revision: 6663d50\n')
    for command in commands:
        stream.write('Command: ' + ' '.join(command) + '\n')
        stream.flush()
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, env=os.environ)
        if result.returncode:
            status = result.returncode
(output / 'regression.done').write_text(str(status) + '\n')
