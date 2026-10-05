import json,subprocess,os
from pathlib import Path
p=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-04-memory-interview-scan')
s=json.loads((p/"identity-correction-command.json").read_text())
with (p/"identity-correction-output.txt").open("w") as log:r=subprocess.run(s["command"],cwd=s["cwd"],env={**os.environ,**s["environment"]},stdout=log,stderr=subprocess.STDOUT)
(p/"identity-correction.done").write_text(str(r.returncode)+"\n")
