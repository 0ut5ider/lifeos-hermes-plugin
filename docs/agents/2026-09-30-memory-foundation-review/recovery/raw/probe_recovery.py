# ABOUTME: Probes native publication recovery using isolated synthetic files and process exits.
# ABOUTME: Records crash ordering, routing, and correction outcomes against actual native tools.
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'tests'))
from test_memory_native import NativeMemoryTests, OWNER
from lifeos_hook_bridge.memory_access import NativeMemory

PRELUDE = '''import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory=NativeMemory(Path(sys.argv[1]))
'''

def run(name, callback):
    test=NativeMemoryTests()
    test.setUp()
    try:
        print(json.dumps({'case':name,'result':callback(test)},sort_keys=True),flush=True)
    finally:
        test.doCleanups()

def child(test, script):
    result=subprocess.run([sys.executable,'-c',PRELUDE+script,str(test.root)],capture_output=True,text=True)
    assert result.returncode==73, (result.returncode,result.stderr)
    return result

def args(title='Recovery ordering'):
    return dict(category='project',content='Synthetic recovery marker',title=title,project='lab')

def crash_before_prepare(test):
    child(test,'''memory.transaction.prepare=lambda *args,**kwargs: os._exit(73)
memory.remember(OWNER,category="project",content="Synthetic recovery marker",title="Recovery ordering",project="lab",request_id="before-prepare")
''')
    memory=NativeMemory(test.root)
    retry=memory.remember(OWNER,request_id='before-prepare',**args())
    return {'retry':retry,'recall':memory.recall(OWNER,'recovery'),'journal_exists':memory.transaction.journal.exists()}

def crash_after_commit(test):
    child(test,'''original=memory.transaction.finish
calls=0
def finish():
    global calls
    calls+=1
    if calls==2: os._exit(73)
    original()
memory.transaction.finish=finish
memory.remember(OWNER,category="project",content="Synthetic recovery marker",title="Recovery ordering",project="lab",request_id="after-commit")
''')
    journal_before=test.memory.transaction.journal.exists()
    memory=NativeMemory(test.root)
    retry=memory.remember(OWNER,request_id='after-commit',**args())
    notes=list((test.root/'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    return {'journal_before_restart':journal_before,'retry':retry,'recall':memory.recall(OWNER,'recovery'),
            'native_occurrences':sum(p.read_text().count('Synthetic recovery marker') for p in notes)}

def crash_sanitized_route(test):
    child(test,'''memory._record=lambda *args,**kwargs: os._exit(73)
memory.remember(OWNER,category="project",content="Synthetic recovery marker",title="<private>hidden</private>Visible",project="lab",request_id="route-crash")
''')
    journal=json.loads(test.memory.transaction.journal.read_text())
    memory=NativeMemory(test.root)
    memory.recall(OWNER,'recovery')
    notes=list((test.root/'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    retained=[p.name for p in notes]
    retry=memory.remember(OWNER,request_id='route-crash',**args('<private>hidden</private>Visible'))
    return {'journal_paths':[c['path'] for c in journal['copies']],'files_after_rollback':retained,
            'retry':retry,'native_occurrences':sum(p.read_text().count('Synthetic recovery marker') for p in notes)}

def crash_hot_correction(test):
    first=test.remember('RULE: synthetic original','hot-original','principal')
    script='''memory._record=lambda *args,**kwargs: os._exit(73)
memory.correct(OWNER,REFERENCE,"RULE: synthetic corrected","hot-correction")
'''.replace('REFERENCE',repr(first['reference']))
    child(test,script)
    memory=NativeMemory(test.root)
    recovered=memory.recall(OWNER,'synthetic')
    retry=memory.correct(OWNER,first['reference'],'RULE: synthetic corrected','hot-correction')
    return {'recovered':recovered,'retry':retry,'after_retry':memory.recall(OWNER,'synthetic')}

run('crash_before_journal_prepare',crash_before_prepare)
run('crash_after_receipt_commit',crash_after_commit)
run('sanitized_title_changes_journal_target',crash_sanitized_route)
run('hot_correction_rollback_and_retry',crash_hot_correction)

def surviving_native_child(test):
    import signal
    saved=test.remember('RULE: synthetic original','original','principal')
    ready=test.home/'native-ready'
    gate=test.home/'native-go'
    done=test.home/'native-done'
    wrapper=test.home/'delay-native.ts'
    wrapper.write_text('''// ABOUTME: Delays a real native write to expose parent-process crash ordering.
// ABOUTME: Runs only against the temporary synthetic fixture supplied by this probe.
import { existsSync, writeFileSync } from 'node:fs';
const input=await Bun.stdin.text();
const request=JSON.parse(input);
if(request.action==='set_hot') {
  writeFileSync(READY,'ready');
  while(!existsSync(GATE)) await Bun.sleep(10);
}
const proc=Bun.spawn(['bun','--no-install',WORKER,process.argv[2]], {
  stdin:new Blob([input]), stdout:'ignore', stderr:'pipe'
});
const stderr=await new Response(proc.stderr).text();
const status=await proc.exited;
if(request.action==='set_hot') writeFileSync(DONE, JSON.stringify({status,stderr}));
// Preliminary reads need their actual native result, so they are handled by Python.
'''.replace('READY',json.dumps(str(ready))).replace('GATE',json.dumps(str(gate)))
       .replace('DONE',json.dumps(str(done))).replace('WORKER',json.dumps(str(test.memory.worker))))
    script=PRELUDE+'''original=memory._native
def native(action,**values):
    if action!="set_hot": return original(action,**values)
    memory.worker=Path(WRAPPER)
    return original(action,**values)
memory._native=native
memory.correct(OWNER,REFERENCE,"RULE: synthetic orphan correction","orphan-correction")
'''.replace('WRAPPER',repr(str(wrapper))).replace('REFERENCE',repr(saved['reference']))
    process=subprocess.Popen([sys.executable,'-c',script,str(test.root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def await_file(path):
        deadline=time.monotonic()+10
        while not path.exists():
            if time.monotonic()>deadline: raise RuntimeError('Timed out waiting for '+path.name)
            time.sleep(0.01)
    try:
        await_file(ready)
        os.kill(process.pid,signal.SIGKILL)
        process.wait(timeout=5)
        memory=NativeMemory(test.root)
        recovered=memory.recall(OWNER,'synthetic')
        committed=memory.remember(OWNER,category='principal',content='RULE: synthetic acknowledged later',
                                 title='',project='',request_id='later-commit')
        gate.write_text('continue')
        await_file(done)
        native=memory._native('read_hot',path=str(test.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'))
        try:
            recall=memory.recall(OWNER,'synthetic')
        except Exception as error:
            recall={'type':type(error).__name__,'error':str(error)}
        return {'python_exit':process.returncode,'recovered_before_later_commit':recovered,
                'later_receipt':committed,'native_after_orphan_finishes':native,'recall':recall,
                'native_child_result':json.loads(done.read_text())}
    finally:
        gate.write_text('continue')
        if process.poll() is None:
            process.kill()
            process.wait()

run('native_child_outlives_parent_and_overwrites_later_commit',surviving_native_child)

def extended_project_body(test):
    content='The synthetic lab uses port 9123'
    saved=test.remember(content,'body-extension')
    note=next((test.root/'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    note.write_text(note.read_text().replace(content,content+' is obsolete; use port 9443.'))
    before=test.memory.recall(OWNER,'9123')
    result=test.memory.correct(OWNER,saved['reference'],'The synthetic lab uses port 9555','correct-extended')
    return {'recall_after_body_change':before,'correction':result}

run('changed_section_retains_original_text_as_prefix',extended_project_body)
