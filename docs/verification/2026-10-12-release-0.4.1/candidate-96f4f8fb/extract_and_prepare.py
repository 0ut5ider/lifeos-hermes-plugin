# ABOUTME: Extracts the sealed candidate with the bounded release catalog before private development preparation.
# ABOUTME: Runs under the development account and detaches preparation without selecting active programs.
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, '/home/lifeos-hermes/releases/qualification-20261012-bunfixed/source')
from optional.lifeos_release_manager.release_catalog import extract_package

root = Path('/home/lifeos-hermes/releases/qualification-20261013-041-96f4f8fb')
extract_package(root / '0.4.1-96f4f8fb.tgz', root / 'source')
environment = dict(os.environ, HOME='/home/lifeos-hermes', HERMES_HOME='/home/lifeos-hermes/.hermes',
                   PYTHONDONTWRITEBYTECODE='1', PATH='/home/lifeos-hermes/.local/bin:/usr/local/bin:/usr/bin:/bin')
with (root / 'prepare-launch.stdout').open('wb') as output, (root / 'prepare-launch.stderr').open('wb') as error:
    process = subprocess.Popen([sys.executable, '-B', str(root / 'prepare_development.py')],
                               env=environment, stdin=subprocess.DEVNULL, stdout=output,
                               stderr=error, start_new_session=True)
(root / 'prepare-launch.pid').write_text(str(process.pid) + '\n')
print('Bounded candidate extraction complete; detached preparation PID', process.pid)
