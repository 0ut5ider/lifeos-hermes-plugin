# ABOUTME: Builds the frozen candidate runtime under an owned synthetic development account.
# ABOUTME: Writes completion markers before installed editor acceptance and account cleanup.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

home = Path('/home/lifeos-editor-acceptance')
folder = home / 'deployment'
archive = home / 'releases/0.5.0-rc.1-02dcd9e3.tgz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'e05fd7aaa57a78fb0b395afb2107e40311f135f294a61226ab482d8b0ac2fbda'
assert hashlib.sha256((home / '.local/bin/bun').read_bytes()).hexdigest() == '7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b'
package = home / 'releases/0.5.0-rc.1-02dcd9e3'
package.mkdir(mode=0o700)
with tarfile.open(archive) as source:
    source.extractall(package, filter='data')
os.environ.update(HOME=str(home), HERMES_HOME=str(home / '.hermes'), PYTHONDONTWRITEBYTECODE='1',
    PATH=str(home / '.local/bin') + ':/usr/local/bin:/usr/bin:/bin')
sys.path.insert(0, str(package / 'hermes'))
code = 1
try:
    import pm
    with (folder / 'python-runtime.stdout').open('w') as out, (folder / 'python-runtime.stderr').open('w') as err:
        from contextlib import redirect_stdout, redirect_stderr
        with redirect_stdout(out), redirect_stderr(err):
            pm.build_environment(source=package / 'python-runtime', out=home / 'venv',
                extras=['discord'], no_install_project=True, frozen=True, explicit=True)
    command = [str(home / 'venv/bin/python'), '-B', str(home / 'releases/install_development_fixture.py')]
    with (folder / 'install.stdout').open('w') as out, (folder / 'install.stderr').open('w') as err:
        result = subprocess.run(command, env=os.environ, stdout=out, stderr=err, timeout=1800)
    code = result.returncode
finally:
    (folder / 'bootstrap.done').write_text(str(code) + '\n')
