# ABOUTME: Runs the fresh distributed interview seed and adjacent native publication gates.
# ABOUTME: Retains raw output and completion across disconnects.
from pathlib import Path
import json,os,subprocess
p=Path(__file__).parent
s=json.loads((p/"final-command.json").read_text())
with (p/"final-output.txt").open("w") as out:
 r=subprocess.run(s["command"],cwd=s["cwd"],env=os.environ|s["environment"],stdout=out,stderr=subprocess.STDOUT)
(p/"final.done").write_text(str(r.returncode)+"\n")
