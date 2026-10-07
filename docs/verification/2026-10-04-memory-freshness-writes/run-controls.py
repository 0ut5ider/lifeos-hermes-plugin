import json,os,pathlib,subprocess
p=pathlib.Path(__file__).parent
s=json.loads((p/"controls-command.json").read_text())
with (p/"controls-output.txt").open("w") as out:
 r=subprocess.run(s["command"],cwd=s["cwd"],env={**os.environ,**s["environment"]},stdout=out,stderr=subprocess.STDOUT)
(p/"controls.done").write_text(str(r.returncode)+"\n")
