import json,os,pathlib,subprocess
p=pathlib.Path(__file__).parent
s=json.loads((p/"before-command.json").read_text())
with (p/"before-output.txt").open("w") as out:
 r=subprocess.run(s["command"],cwd=s["cwd"],env={**os.environ,**s["environment"]},stdout=out,stderr=subprocess.STDOUT)
(p/"before.done").write_text(str(r.returncode)+"\n")
