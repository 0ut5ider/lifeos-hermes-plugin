# ABOUTME: Verifies repaired publication ordering and reference behavior in temporary fixtures.
# ABOUTME: Uses real native operations and deterministic child-process crash boundaries.
import ast
import json
from pathlib import Path
import threading
import time

prior=Path('docs/agents/2026-09-30-memory-foundation-review/recovery/raw/probe_recovery.py')
module=ast.parse(prior.read_text(),filename=str(prior))
module.body=[node for node in module.body if not (isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
             and isinstance(node.value.func,ast.Name) and node.value.func.id=='run')]
exec(compile(module,str(prior),'exec'),globals())

def commit_crash(test):
    child(test,'''memory.transaction.finish=lambda: os._exit(73)
memory.remember(OWNER,category="project",content="Synthetic recovery marker",title="Recovery ordering",project="lab",request_id="after-commit")
''')
    before=test.memory.transaction.journal.exists()
    memory=NativeMemory(test.root)
    retry=memory.remember(OWNER,request_id='after-commit',**args())
    return {'journal_before':before,'retry':retry,'recall':memory.recall(OWNER,'recovery')}

def title_validation(test):
    result=test.memory.remember(OWNER,request_id='private-title',**args('<private>hidden</private>Visible'))
    return {'result':result,'native_files':[str(p.relative_to(test.root)) for p in (test.root/'LIFEOS/MEMORY/KNOWLEDGE').rglob('*.md')]}

def guarded_child(test):
    # The old probe releases the gate after recall; release asynchronously because recall now waits.
    def release():
        ready=test.home/'native-ready'
        deadline=time.monotonic()+10
        while not ready.exists():
            if time.monotonic()>deadline: return
            time.sleep(0.01)
        time.sleep(0.5)
        (test.home/'native-go').write_text('continue')
    releaser=threading.Thread(target=release)
    releaser.start()
    try:
        return surviving_native_child(test)
    finally:
        releaser.join(timeout=12)

def changed_prefix(test):
    content='The synthetic lab uses port 9123'
    saved=test.remember(content,'body-extension')
    note=next((test.root/'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    note.write_text(note.read_text().replace(content,content+' is obsolete; use port 9443.'))
    return {'correction':test.memory.correct(OWNER,saved['reference'],'The synthetic lab uses port 9555','correct-extended')}

def heading_in_fact(test):
    content='Synthetic first paragraph\n## Appended experiment notes\nSynthetic second paragraph'
    saved=test.remember(content,'heading-content')
    try:
        found=test.memory.recall(OWNER,'Synthetic')
    except Exception as error:
        found={'type':type(error).__name__,'error':str(error)}
    return {'saved':saved,'recall':found}

run('crash_before_journal_prepare',crash_before_prepare)
run('crash_after_receipt_commit',commit_crash)
run('sanitized_title_rejected_before_routing',title_validation)
run('hot_correction_rollback_and_retry',crash_hot_correction)
run('native_child_lock_serializes_recovery',guarded_child)
run('changed_project_prefix_conflicts',changed_prefix)
run('allowed_markdown_heading_conflicts_with_section_parser',heading_in_fact)
