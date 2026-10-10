# ABOUTME: Runs native Knowledge command and neighboring memory checks against one prepared source pair.
# ABOUTME: Records exact runtime versions, child output, and a durable completion result.
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
environment=dict(os.environ,PATH=str(Path.home()/'.bun/bin')+os.pathsep+os.environ['PATH'],
    PYTHONPATH=os.pathsep.join((str(root),str(root/'tests'),str(hermes))),LIFEOS_MEMORY_SOURCE=str(lifeos),
    LIFEOS_HERMES_SOURCE=str(hermes),LIFEOS_HERMES_REBUILD_SOURCE=str(hermes))
modules=['test_memory_knowledge_views','test_memory_knowledge_harvest','test_memory_staging',
    'test_memory_staging_writers','test_memory_canonical','test_memory_native','test_memory_backup',
    'test_memory_delegation','test_memory_background_audience','test_memory_knowledge_render',
    'test_memory_knowledge_relay','test_memory_knowledge_query','test_patch_bundle',
    'test_lifeos_install_source','test_capability_validation']
signal.signal(signal.SIGINT,signal.default_int_handler)
with (evidence/'combined-final.txt').open('w') as output:
    result=subprocess.run([sys.executable,'-W','error','-m','unittest',*modules,'-v'],env=environment,
                          cwd=root,stdout=output,stderr=subprocess.STDOUT,check=False)
receipt={'exit_code':result.returncode,'modules':modules,'hermes':str(hermes),'lifeos':str(lifeos),
    'versions':{name:importlib.metadata.version(name) for name in ('fastapi','starlette','anyio','httpx')}}
(evidence/'gate-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
(evidence/'focused.done').write_text(str(result.returncode)+'\n')
sys.exit(result.returncode)
