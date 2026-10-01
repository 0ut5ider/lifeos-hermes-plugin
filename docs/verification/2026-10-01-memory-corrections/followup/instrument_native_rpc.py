# ABOUTME: Records native action counts and callers for synthetic governed RPC requests.
# ABOUTME: Delegates every action unchanged to the actual native implementation.
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback
# The owned probe sets the exact reviewed project import path explicitly.
sys.path.insert(0,os.environ['LIFEOS_REVIEW_PROJECT'])
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_rpc import main
wire=sys.stdin.buffer.read()
operation=json.loads(wire)['operation']
sys.stdin=io.TextIOWrapper(io.BytesIO(wire),encoding='utf-8')
real_native=NativeMemory._native
def observe(self, action, **values):
    started=time.monotonic()
    frames=traceback.extract_stack(limit=5)
    try:
        return real_native(self,action,**values)
    finally:
        record={'operation':operation,'action':action,'seconds':time.monotonic()-started,
            'path':values.get('path'),'callers':[{'function':frame.name,'line':frame.lineno,
                'file':Path(frame.filename).name} for frame in frames[:-1]]}
        with Path(os.environ['LIFEOS_REVIEW_CALL_LOG']).open('a') as log:
            log.write(json.dumps(record)+'\n')
NativeMemory._native=observe
main()
