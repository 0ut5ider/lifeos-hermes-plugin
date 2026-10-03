# ABOUTME: Checks audit recovery and identical retries across hot mutation entry points.
# ABOUTME: Uses actual native publication and interrupts after set_hot returns in a child.
import json
from pathlib import Path
import subprocess
import sys
import test_memory_native as native
from lifeos_hook_bridge.memory_access import HOT_FILES
out=Path(__file__).parent
results=[]
for category in ('principal','assistant'):
    for operation in ('correct','forget','native_set'):
        f=native.NativeMemoryTests();f.setUp()
        try:
            first=f.remember('RULE: Synthetic transaction target','target',category)
            second=f.remember('RULE: Synthetic transaction neighbor','neighbor',category)
            before=f.memory.read_hot(native.OWNER,category)
            hot=f.root/HOT_FILES[category]
            log=f.root/'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl'
            oldhot,oldlog=hot.read_bytes(),log.read_bytes()
            arguments=[native.OWNER,first['reference']]
            if operation=='correct': arguments.append('RULE: Synthetic transaction replacement')
            arguments.append('interrupted-mutation')
            if operation=='native_set':
                arguments=[native.OWNER,category,['RULE: Synthetic transaction replacement','RULE: Synthetic transaction neighbor'],
                    'interrupted-mutation',before['revision']]
            # The child executes the same call with the real scope imported in its own interpreter.
            call_arguments=repr(arguments[1:])
            script='''import os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_native import OWNER
memory=NativeMemory(Path(sys.argv[1]))
real_native=memory._native
def interrupt(action, **values):
    result=real_native(action, **values)
    if action=='set_hot' and result.get('ok'):
        os._exit(73)
    return result
memory._native=interrupt
getattr(memory, sys.argv[2])(OWNER, *ARGS)
'''.replace('ARGS',call_arguments)
            child=subprocess.run([sys.executable,'-c',script,str(f.root),operation],capture_output=True,text=True,timeout=40)
            assert child.returncode==73,child.stderr
            during={'hot':hot.read_text(),'log':log.read_text(),'journal':json.loads(f.memory.transaction.journal.read_text())}
            restored=f.memory.read_hot(native.OWNER,category)
            assert hot.read_bytes()==oldhot
            assert log.read_bytes()==oldlog
            assert f.memory.get(native.OWNER,first['reference'])['status']=='ok'
            receipt=getattr(f.memory,operation)(*arguments)
            retried=getattr(f.memory,operation)(*arguments)
            assert receipt==retried,(receipt,retried)
            status=receipt.get('receipt',receipt)['status']
            assert status=='committed',receipt
            assert f.memory.get(native.OWNER,second['reference'])['status']=='ok'
            results.append({'category':category,'operation':operation,'child_exit':child.returncode,
                'before_hot':oldhot.decode(),'before_log':oldlog.decode(),'interrupted':during,
                'restored':restored,'audit_prefix_restored':True,'receipt':receipt,'retry':retried})
        finally:f.doCleanups()
# A previously absent audit file must remain absent after recovery.
f=native.NativeMemoryTests();f.setUp()
try:
    log=f.root/'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl'
    assert not log.exists()
    script='''import os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_native import OWNER
memory=NativeMemory(Path(sys.argv[1]))
memory._record=lambda *args,**kwargs:os._exit(73)
memory.remember(OWNER,category='principal',content='RULE: Synthetic missing-log candidate',
    title='',project='',request_id='first-interrupted')
'''
    child=subprocess.run([sys.executable,'-c',script,str(f.root)],capture_output=True,text=True,timeout=40)
    assert child.returncode==73,child.stderr
    assert log.exists()
    restored=f.memory.read_hot(native.OWNER,'principal')
    assert restored['entries']==[] and not log.exists()
    saved=f.remember('RULE: Synthetic missing-log candidate','first-interrupted','principal')
    assert saved['status']=='committed',saved
    assert f.remember('RULE: Synthetic missing-log candidate','first-interrupted','principal')==saved
    results.append({'operation':'missing-log-recovery','restored':restored,'audit_absent_after_recovery':True,'saved':saved})
finally:f.doCleanups()
(out/'recovery-contracts-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps([{'operation':r['operation'],'category':r.get('category'),
    'audit_restored':r.get('audit_prefix_restored',r.get('audit_absent_after_recovery'))} for r in results],indent=2))
