import json,subprocess,os
from pathlib import Path
p=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-04-memory-interview-due')
s=json.loads((p/"expanded-command.json").read_text())
with (p/"expanded-output.txt").open("w") as log:r=subprocess.run(s["command"],cwd=s["cwd"],env={**os.environ,**s["environment"]},stdout=log,stderr=subprocess.STDOUT)
(p/"expanded.done").write_text(str(r.returncode)+"\n")
