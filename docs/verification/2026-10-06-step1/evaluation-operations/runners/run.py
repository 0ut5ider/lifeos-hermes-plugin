import subprocess
from pathlib import Path
p=Path('/var/tmp/lifeos-step1-20261006/evaluation-operations-final')
r=subprocess.run(["/usr/local/bin/python3",str(p/"evaluation_operation_controls.py"),'/var/tmp/lifeos-step1-20261006/evaluation-operations-final-configuration.json',str(p/"evaluation-operations-final-results")])
(p/"run.done").write_text(str(r.returncode)+"\n")
