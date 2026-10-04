import json,subprocess,os
from pathlib import Path
p=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-04-memory-state-evidence')
s=json.loads((p/"final-command.json").read_text())
with (p/"final-output.txt").open("w") as log:r=subprocess.run(s["command"],cwd=s["cwd"],env={**os.environ,**s["environment"]},stdout=log,stderr=subprocess.STDOUT)
(p/"final.done").write_text(str(r.returncode)+"\n")
