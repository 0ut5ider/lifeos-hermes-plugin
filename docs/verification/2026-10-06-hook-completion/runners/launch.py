import os,subprocess,sys
from pathlib import Path
root=Path(__file__).parent
name=sys.argv[1]
env={**os.environ,"PATH":"/home/lifeos-claude-ref/.bun/bin:/usr/local/bin:/usr/bin:/bin","PYTHONPATH":str(root)+":/var/tmp/lifeos-agent-invocation-20261006/hermes"}
with (root/(name+".log")).open("w") as log:
 result=subprocess.run(sys.argv[2:],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
(root/(name+".done")).write_text(str(result.returncode)+"\n")
