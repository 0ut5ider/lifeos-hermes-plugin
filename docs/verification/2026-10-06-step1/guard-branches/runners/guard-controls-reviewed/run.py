# ABOUTME: Runs isolated paired native and Hermes controls.
# ABOUTME: Persists completion and failures after disconnection.
import json,traceback
from pathlib import Path
from paired_lifecycle_effects import run_controls
root=Path(__file__).resolve().parent
code=1
try:
 code=run_controls(json.loads((root/"configuration.json").read_text()),root/"results",['guard-bash-system-clean', 'guard-bash-system-user', 'guard-bash-public-block'])
except BaseException:
 traceback.print_exc()
finally:
 (root/"run.done").write_text(str(code)+"\n")
