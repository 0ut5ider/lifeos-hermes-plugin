# ABOUTME: Runs all memory regression modules against the selected prepared native sources.
# ABOUTME: Saves child output, exact source and runtime selection, and a persistent completion marker.
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

root=Path(__file__).resolve().parents[3]
evidence=Path(__file__).resolve().parent
hermes=Path(sys.argv[1]).resolve()
lifeos=Path(sys.argv[2]).resolve()
control=Path(sys.argv[3]).resolve()
modules=[path.stem for path in sorted((root/'tests').glob('test_memory*.py'))]
environment=dict(os.environ,PATH=str(Path.home()/'.bun/bin')+os.pathsep+os.environ['PATH'],
    PYTHONPATH=os.pathsep.join((str(root),str(root/'tests'),str(hermes))),LIFEOS_MEMORY_SOURCE=str(lifeos),
    LIFEOS_HERMES_SOURCE=str(hermes),LIFEOS_HERMES_REBUILD_SOURCE=str(hermes),
    LIFEOS_FRESHNESS_CONTROL_SOURCE=str(control))
signal.signal(signal.SIGINT,signal.default_int_handler)
receipt={'modules':modules,'hermes':str(hermes),'lifeos':str(lifeos),'control':str(control),
    'workers':3,'isolation':'one unittest process per module',
    'plugin_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    'versions':{name:importlib.metadata.version(name) for name in ('fastapi','starlette','anyio','httpx')}}
(evidence/'regression-command.json').write_text(json.dumps(receipt,indent=2)+'\n')
logs=evidence/'regression-modules'
logs.mkdir(exist_ok=True)
def run(module):
    command=[sys.executable,'-W','error','-m','unittest',module,'-v']
    with (logs/(module+'.txt')).open('w') as output:
        result=subprocess.run(command,env=environment,cwd=root,stdout=output,stderr=subprocess.STDOUT,check=False)
    status={'module':module,'exit_code':result.returncode,'command':command}
    (logs/(module+'.json')).write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    return status
with ThreadPoolExecutor(max_workers=3) as workers:
    receipt['results']=list(workers.map(run,modules))
receipt['exit_code']=int(any(result['exit_code'] for result in receipt['results']))
(evidence/'regression-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
(evidence/'regression.done').write_text(str(receipt['exit_code'])+'\n')
sys.exit(receipt['exit_code'])
