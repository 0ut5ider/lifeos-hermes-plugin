# ABOUTME: Runs ownership configuration and adjacent recovery controls.
# ABOUTME: Saves output and completion state across disconnects.
from pathlib import Path
import json, os, subprocess
e=Path(__file__).parent
s=json.loads((e/"final-command.json").read_text())
with (e/"final-output.txt").open("w") as out:
 r=subprocess.run(s["command"],cwd=s["cwd"],env=os.environ|s["environment"],stdout=out,stderr=subprocess.STDOUT)
(e/"final.done").write_text(str(r.returncode)+"\n")
