# ABOUTME: Runs ownership configuration and actual Hermes controls.
# ABOUTME: Saves output and completion state across disconnects.
from pathlib import Path
import json, os, subprocess
e=Path(__file__).parent
s=json.loads((e/"expanded-command.json").read_text())
with (e/"expanded-output.txt").open("w") as out:
 r=subprocess.run(s["command"],cwd=s["cwd"],env=os.environ|s["environment"],stdout=out,stderr=subprocess.STDOUT)
(e/"expanded.done").write_text(str(r.returncode)+"\n")
