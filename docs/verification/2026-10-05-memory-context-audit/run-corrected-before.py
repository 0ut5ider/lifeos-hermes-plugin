from pathlib import Path
import json,os,subprocess
p=Path(__file__).parent
s=json.loads((p/"corrected-before-command.json").read_text())
with (p/"corrected-before-output.txt").open("w") as out:
 r=subprocess.run(s["command"],cwd=s["cwd"],env=os.environ|s["environment"],stdout=out,stderr=subprocess.STDOUT)
(p/"corrected-before.done").write_text(str(r.returncode)+"\n")
