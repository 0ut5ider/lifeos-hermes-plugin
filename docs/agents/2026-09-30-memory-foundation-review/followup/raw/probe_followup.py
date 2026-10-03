# ABOUTME: Reproduces foundation review findings with disposable synthetic native fixtures.
# ABOUTME: Prints real native outcomes and retained metadata without reading installed user data.
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'tests'))
from test_memory_native import NativeMemoryTests, OWNER

def safe_recall(test, query):
    try:
        return test.memory.recall(OWNER, query)
    except Exception as error:
        return {'type':type(error).__name__, 'error':str(error)}

def run(name, callback):
    test = NativeMemoryTests()
    test.setUp()
    try:
        result = callback(test)
        print(json.dumps({'case': name, 'result': result}, sort_keys=True))
    finally:
        test.doCleanups()

def hot_file(test):
    return test.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'

def malformed(test):
    saved = test.remember('RULE: original synthetic marker', 'original', 'principal')
    receipt = test.memory.correct(OWNER, saved['reference'], 'RULE: first line\nsecond line', 'malformed')
    current = test.memory._native('read_hot', path=str(hot_file(test)))
    try:
        recall = test.memory.recall(OWNER, 'original')
    except Exception as error:
        recall = {'error': str(error), 'type': type(error).__name__}
    return {'saved': saved, 'correction': receipt, 'native_read': current, 'recall': recall,
            'retry': test.memory.correct(OWNER, saved['reference'], 'RULE: first line\nsecond line', 'malformed')}

def privacy(test):
    saved = test.remember('RULE: original synthetic marker', 'original', 'principal')
    content = 'RULE: public <private>SYNTHETIC_DENIED_MARKER</private>'
    validation = test.memory._native('validate', item={'type':'memory', 'actor':'principal', 'content':content})
    receipt = test.memory.correct(OWNER, saved['reference'], content, 'privacy')
    return {'native_validation': validation, 'correction': receipt, 'recall': test.memory.recall(OWNER, 'SYNTHETIC_DENIED_MARKER')}

def tombstone(test):
    saved = test.remember('Synthetic forgotten marker', 'forgotten')
    forgotten = test.memory.forget(OWNER, saved['reference'], 'forget')
    ordinary = test.remember('Synthetic forgotten marker', 'remember-again')
    other = test.remember('Synthetic alternative marker', 'other')
    correction = test.memory.correct(OWNER, other['reference'], 'Synthetic forgotten marker', 'reactivate-via-correction')
    return {'forgotten':forgotten, 'ordinary_remember':ordinary, 'correction':correction,
            'recall':test.memory.recall(OWNER, 'forgotten')}

def duplicate_hot(test):
    first = test.remember('RULE: synthetic duplicate marker', 'one', 'principal')
    second = test.memory.remember(OWNER, category='principal', content='RULE: synthetic duplicate marker',
                                 title='', project='', request_id='two')
    forgotten = test.memory.forget(OWNER, first['reference'], 'forget-first')
    try:
        recall = test.memory.recall(OWNER, 'duplicate')
    except Exception as error:
        recall = {'error':str(error)}
    return {'first':first, 'second':second, 'forget':forgotten, 'recall':recall}

for name, callback in [('malformed_hot_correction',malformed), ('private_hot_correction',privacy),
                       ('forgotten_correction',tombstone), ('duplicate_hot_project_metadata', duplicate_hot)]:
    run(name, callback)

def merged_hot(test):
    first = test.remember('RULE: synthetic alpha marker', 'one', 'principal')
    second = test.remember('RULE: synthetic beta marker', 'two', 'principal')
    correction = test.memory.correct(OWNER, first['reference'], 'RULE: synthetic beta marker', 'merge')
    before = test.memory.recall(OWNER, 'beta')
    forgotten = test.memory.forget(OWNER, second['reference'], 'forget-second')
    try:
        after = test.memory.recall(OWNER, 'beta')
    except Exception as error:
        after = {'error':str(error)}
    return {'correction':correction, 'before':before, 'forget':forgotten, 'after':after}

def ambiguous_reference(test):
    first = test.remember('Synthetic section original marker', 'one')
    note = next((test.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    text = note.read_text()
    # Simulate a changed target section and two retained quotations of its previous value.
    note.write_text(text.replace('Synthetic section original marker', 'Synthetic section changed marker') +
                    '\n## Unrelated retained quotations\nSynthetic section original marker\nSynthetic section original marker\n')
    correction = test.memory.correct(OWNER, first['reference'], 'Synthetic replacement marker', 'correct-ambiguous')
    return {'correction':correction, 'recall':safe_recall(test, 'replacement')}

run('correction_merges_existing_hot_entry', merged_hot)
run('ambiguous_reference_accepted', ambiguous_reference)

def interrupted_write(test):
    import subprocess
    from lifeos_hook_bridge.memory_access import NativeMemory
    child = '''import os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory = NativeMemory(Path(sys.argv[1]))
def stop_after_native(*args, **kwargs):
    os._exit(73)
memory._record = stop_after_native
memory.remember(OWNER, category="project", content="Synthetic crash marker", title="Crash recovery", project="lab", request_id="crash")
'''
    completed = subprocess.run([sys.executable, '-c', child, str(test.root)], capture_output=True, text=True)
    memory = NativeMemory(test.root)
    arguments = dict(category='project', content='Synthetic crash marker', title='Crash recovery', project='lab')
    retry = memory.remember(OWNER, request_id='crash', **arguments)
    after_restart = memory.recall(OWNER, 'crash')
    fresh_key = memory.remember(OWNER, request_id='new-request', **arguments)
    note = next((test.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    return {'child_exit':completed.returncode, 'child_stderr':completed.stderr, 'retry':retry,
            'recall_after_restart':after_restart, 'new_key':fresh_key,
            'native_fact_occurrences_after_new_key':note.read_text().count('Synthetic crash marker')}

run('interrupted_native_publication', interrupted_write)

def unicode_hot(test):
    saved = test.remember('RULE: original synthetic marker', 'original', 'principal')
    replacement = 'RULE: ' + chr(0x1F600) * 129
    result = test.memory.correct(OWNER, saved['reference'], replacement, 'unicode')
    return {'python_body_length':129, 'javascript_utf16_body_length':258, 'correction':result,
            'native_read':test.memory._native('read_hot', path=str(hot_file(test))),
            'recall':safe_recall(test, 'original')}

def title_alias(test):
    content = 'Synthetic exact title marker'
    saved = test.memory.remember(OWNER, category='project', content=content, title=content,
                                 project='lab', request_id='title-alias')
    note = next((test.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    text = note.read_text()
    position = text.rfind(content)
    assert position >= 0
    note.write_text(text[:position] + text[position:].replace(content, 'Synthetic changed body marker', 1))
    before = safe_recall(test, 'exact title')
    result = test.memory.correct(OWNER, saved['reference'], 'Synthetic replacement marker', 'correct-stale-body')
    return {'recall_after_body_change':before,'correction':result,'note':note.read_text()}

def unchanged_and_merge(test):
    import sqlite3
    first = test.remember('RULE: synthetic alpha marker', 'one', 'principal')
    unchanged = test.memory.correct(OWNER, first['reference'], 'synthetic alpha marker', 'same')
    second = test.remember('RULE: synthetic beta marker', 'two', 'principal')
    merge = test.memory.correct(OWNER, first['reference'], 'RULE: synthetic beta marker', 'merge')
    stale = test.memory.correct(OWNER, first['reference'], 'RULE: synthetic third marker', 'stale')
    with sqlite3.connect(test.memory.database) as connection:
        rows = connection.execute('SELECT id, revision, status, project FROM records ORDER BY status').fetchall()
    return {'first':first,'second':second,'unchanged':unchanged,'merge':merge,'stale':stale,'records':rows,
            'native_read':test.memory._native('read_hot', path=str(hot_file(test)))}

run('unicode_overlength_hot_correction', unicode_hot)
run('project_reference_binds_title_instead_of_body', title_alias)
run('exact_unchanged_merge_state', unchanged_and_merge)
