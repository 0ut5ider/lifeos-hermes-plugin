# ABOUTME: Observes real hypothesis review rendering and interrupts actual owner publications.
# ABOUTME: Applies synthetic source and authority changes without replacing native responses.
import json
import os
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import lifeos_hook_bridge.memory_hypothesis_review as review

configuration=MemoryConfiguration(Path(sys.argv[1]))
mode=sys.argv[2]
root=Path(configuration.load()['root'])
frames=root/review.FRAMES
original=NativeMemory._native
rendered=False


def observe(memory,action,**arguments):
    global rendered
    result=original(memory,action,**arguments)
    if action=='hypothesis_review':
        rendered=True
        if mode=='authority':configuration.update(lambda value:value['accounts'].clear())
        elif mode=='source':
            path=frames/'_hypotheses/2026-10-08_synthetic-hypothesis.md'
            path.write_text(path.read_text().replace('SyntheticHypothesisCurrentMarker','SyntheticHypothesisChangedMarker'))
        elif mode=='frame':(frames/'synthetic-hypothesis.md').write_text('Synthetic later frame')
        elif mode=='archive':
            path=frames/'_hypotheses/_archive/2026-10-08_synthetic-hypothesis.md'
            path.parent.mkdir(exist_ok=True)
            path.write_text('Synthetic later archive')
        elif mode=='state':(frames/'_hypotheses/.state.json').write_text('{"synthetic_later_state":true}')
    return result


NativeMemory._native=observe
original_publish=review.publish


def interrupt(path,data,**arguments):
    original_publish(path,data,**arguments)
    selected={'interrupt-frame':'synthetic-hypothesis.md','interrupt-archive':'_archive/2026-10-08_synthetic-hypothesis.md',
        'interrupt-state':'.state.json'}.get(mode)
    if selected is not None and str(path).endswith('/'+selected):os._exit(73)


review.publish=interrupt
original_unlink=Path.unlink


def unlink(path,**arguments):
    result=original_unlink(path,**arguments)
    if mode=='interrupt-delete' and path==frames/'_hypotheses/2026-10-08_synthetic-hypothesis.md':os._exit(73)
    return result


Path.unlink=unlink
preferences=MemoryPreferences(configuration.path,root,Path(sys.executable),
    Path(__file__).resolve().parents[1]/'lifeos_hook_bridge/memory_rpc.py')
try:
    result=preferences.review_hypothesis('/api/hypotheses/synthetic-hypothesis/graduate',None,
        'synthetic-review-'+mode,account='dashboard:basic:synthetic-owner')
except (PermissionError,RuntimeError,OSError,ValueError):
    print(json.dumps({'rendered':rendered,'withheld':True}))
else:print(json.dumps({'rendered':rendered,'withheld':False,'result':result}))
