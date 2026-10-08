# ABOUTME: Runs all memory regression modules against the selected prepared native sources.
# ABOUTME: Saves child output, exact source and runtime selection, and a persistent completion marker.
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

root=Path(__file__).resolve().parents[3]
evidence=Path(__file__).resolve().parent
hermes=Path(sys.argv[1]).resolve()
lifeos=Path(sys.argv[2]).resolve()
modules=[path.stem for path in sorted((root/'tests').glob('test_memory*.py'))]
environment=dict(os.environ,PATH=str(Path.home()/'.bun/bin')+os.pathsep+os.environ['PATH'],
    PYTHONPATH=os.pathsep.join((str(root),str(root/'tests'),str(hermes))),LIFEOS_MEMORY_SOURCE=str(lifeos),
    LIFEOS_HERMES_SOURCE=str(hermes),LIFEOS_HERMES_REBUILD_SOURCE=str(hermes))
signal.signal(signal.SIGINT,signal.default_int_handler)
receipt={'modules':modules,'hermes':str(hermes),'lifeos':str(lifeos),
    'versions':{name:importlib.metadata.version(name) for name in ('fastapi','starlette','anyio','httpx')}}
(evidence/'regression-command.json').write_text(json.dumps(receipt,indent=2)+'\n')
with (evidence/'regression.txt').open('w') as output:
    result=subprocess.run([sys.executable,'-W','error','-m','unittest',*modules,'-v'],env=environment,
                          cwd=root,stdout=output,stderr=subprocess.STDOUT,check=False)
receipt['exit_code']=result.returncode
(evidence/'regression-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
(evidence/'regression.done').write_text(str(result.returncode)+'\n')
sys.exit(result.returncode)
