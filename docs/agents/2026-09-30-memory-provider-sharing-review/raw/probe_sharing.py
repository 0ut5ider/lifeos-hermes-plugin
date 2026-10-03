# ABOUTME: Probes config update concurrency and SSH revocation ownership in synthetic files.
# ABOUTME: Never opens a network connection or changes actual authorized keys.
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_sharing import MemorySharingTests,public_key
from lifeos_hook_bridge.memory_service import MemoryConfiguration

def run(name,fn):
    f=MemorySharingTests();f.setUp()
    try: print(json.dumps({'case':name,'result':fn(f)},sort_keys=True),flush=True)
    finally:f.doCleanups()

def separate_process_updates(f):
    program='''from pathlib import Path
import sys
from lifeos_hook_bridge.memory_service import MemoryConfiguration
config=MemoryConfiguration(Path(sys.argv[1]))
for i in range(8):
    def change(value):
        value.setdefault('process_updates',{})[sys.argv[2]+'-'+str(i)]=True
        if sys.argv[2]=='0': value['clients']['research']['enabled']=False
    config.update(change)
'''
    def child(index):
        proc=subprocess.run([sys.executable,'-c',program,str(f.fixture.config),str(index)],capture_output=True,text=True,timeout=30)
        assert proc.returncode==0,(proc.returncode,proc.stderr)
        return {'process':index,'exit_code':proc.returncode,'stderr':proc.stderr}
    with ThreadPoolExecutor(max_workers=4) as pool: children=list(pool.map(child,range(4)))
    config=MemoryConfiguration(f.fixture.config).load()
    assert len(config['process_updates'])==32 and not config['clients']['research']['enabled']
    return {'children':children,'updates':len(config['process_updates']),'research_enabled':config['clients']['research']['enabled']}

def comment_collision(f):
    unrelated=public_key(41)+' lifeos-memory:researcher\n'
    f.keys.write_text(unrelated)
    result=f.sharing.enroll('researcher',public_key(42),projects=['lab'],model_route='unknown')
    before=f.keys.read_text()
    revoked=f.sharing.revoke('researcher')
    after=f.keys.read_text()
    return {'enrolled':result['status'],'before':before,'revoked':revoked,'after':after,'unrelated_key_preserved':public_key(41) in after}

run('separate_process_configuration_updates',separate_process_updates)
run('revocation_comment_collision',comment_collision)
