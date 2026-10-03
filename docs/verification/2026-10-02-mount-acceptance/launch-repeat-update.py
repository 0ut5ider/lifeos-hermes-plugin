# ABOUTME: Loads the installed Hermes dependency environment for the acceptance operator.
# ABOUTME: Runs only the fixed update rehearsal script in the isolated home.
from pathlib import Path
import subprocess
from hermes_cli import _launchers

home = Path.home()
code = "worker = sys.argv.pop(1)\nsys.argv[0] = worker\nrunpy.run_path(worker, run_name='__main__')\n"
command = _launchers.runtime_command(home / 'workspace/hermes', [str(home / 'repeat-update.py')], code=code)
raise SystemExit(subprocess.run(command).returncode)
