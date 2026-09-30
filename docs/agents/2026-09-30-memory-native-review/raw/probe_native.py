# ABOUTME: Exercises delegated native archive, curation, and reviewer privacy edge cases.
# ABOUTME: Uses real native tools and temporary synthetic configuration and fact files.
from datetime import datetime,timezone
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import NativeMemoryTests,OWNER
from test_memory_delegation import MemoryDelegationTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration

def run(name,kind,callback):
    fixture=kind(); fixture.setUp()
    try: print(json.dumps({'case':name,'result':callback(fixture)},sort_keys=True),flush=True)
    finally: fixture.doCleanups()

def outcome(callback):
    try: return callback()
    except Exception as error: return {'raised':type(error).__name__,'message':str(error)}

def related_link_shift(test):
    memory=test.memory
    first=memory.native_add(OWNER,{'type':'knowledge','entity_type':'research','name':'Synthetic linked note','content':'Synthetic original linked fact'},request_id='one',project='lab')
    reference=first['receipt']['reference']
    second=memory.native_add(OWNER,{'type':'knowledge','entity_type':'research','name':'Synthetic linked note','content':'Synthetic second linked fact',
                                  'related':[{'slug':'synthetic-target','type':'related'}]},request_id='two',project='lab')
    return {'first':first,'second':second,'get_first':outcome(lambda:memory.get(OWNER,reference)),
            'recall':outcome(lambda:memory.recall(OWNER,'synthetic linked'))}

def provenance_only_curation(test):
    memory=test.memory
    first=test.remember('RULE: original retained fact','one','principal')
    read=memory.read_hot(OWNER,'principal')
    changed=memory.native_set(OWNER,'principal',['PREFERENCE: Original retained fact ~inferred'],'provenance',read['revision'])
    return {'changed':changed,'recall':memory.recall(OWNER,'retained fact'),
            'filter_current_claim':memory.filter_history(OWNER,'Today confirms original retained fact',datetime.now(timezone.utc).isoformat()),
            'remember_current':test.remember('PREFERENCE: Original retained fact ~inferred','remember-current','principal')}

def restricted_reviewer(test):
    test.fixture.remember('RULE: synthetic private reviewer marker','private','principal')
    config=test.configuration.load()
    config['destinations']['chat-a:200']['read']=['project']
    config['destinations']['chat-a:200']['write']=['project']
    test.configuration.save(config)
    prompt=test.call([{'name':'review_prompt','exchanges':[{'ts':datetime.now(timezone.utc).isoformat(),
        'user':'Earlier private memory said synthetic private reviewer marker','assistant':'Keep this private memory rule.'}]}])[0]
    return {'prompt':prompt}

run('related_links_preserve_record_offsets',NativeMemoryTests,related_link_shift)
run('normalized_current_claim_is_not_a_tombstone',NativeMemoryTests,provenance_only_curation)
run('project_only_reviewer_input',MemoryDelegationTests,restricted_reviewer)

def person_correction_crash(test):
    import os,subprocess
    from lifeos_hook_bridge.memory_access import NativeMemory
    item={'type':'knowledge','entity_type':'person','name':'Synthetic Person','content':'Synthetic original person fact'}
    first=test.memory.native_add(OWNER,item,request_id='person',project='lab')
    reference=first['receipt']['reference']
    script='''import os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import NativeMemory
memory=NativeMemory(Path(sys.argv[1]))
memory._record=lambda *args,**kwargs: os._exit(73)
memory.correct(OWNER,REFERENCE,'Synthetic corrected person fact','correct-person')
'''.replace('REFERENCE',repr(reference))
    child=subprocess.run([sys.executable,'-c',script,str(test.root)],capture_output=True,text=True)
    assert child.returncode==73,(child.returncode,child.stderr)
    journal=json.loads(test.memory.transaction.journal.read_text())
    memory=NativeMemory(test.root)
    recovered=memory.get(OWNER,reference)
    retained=[str(path.relative_to(test.root)) for path in (test.root/'LIFEOS/MEMORY/KNOWLEDGE').rglob('*.md')]
    retry=memory.correct(OWNER,reference,'Synthetic corrected person fact','correct-person')
    research=list((test.root/'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    return {'first_path':first['path'],'journal_paths':[copy['path'] for copy in journal['copies']],
            'recovered':recovered,'files_after_recovery':retained,'retry':retry,
            'research_correction_occurrences':sum(p.read_text().count('Synthetic corrected person fact') for p in research)}

def native_idea_filter(test):
    item={'type':'idea','title':'Synthetic native idea','content':'Synthetic idea marker'}
    saved=test.memory.native_add(OWNER,item,request_id='idea',project='lab')
    return {'saved':saved,'ideas':test.memory.relevant_context(OWNER,'synthetic idea',{'typeFilter':'idea'}),
            'knowledge':test.memory.relevant_context(OWNER,'synthetic idea',{'typeFilter':'knowledge'})}

def malformed_and_revoked(test):
    first=test.call([{'name':'add','item':{'type':'memory','actor':'principal','content':'RULE: synthetic granted native marker'}}])
    config=test.configuration.load()
    config['destinations']['chat-a:200']['read']=[]
    config['destinations']['chat-a:200']['write']=[]
    test.configuration.save(config)
    revoked=test.call([{'name':'add','item':{'type':'memory','actor':'principal','content':'RULE: synthetic revoked write'}},
                       {'name':'rank','query':'synthetic granted native marker'},
                       {'name':'read','path':str(test.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md')}])
    return {'first':first,'revoked':revoked}

run('nonresearch_correction_targets_unjournaled_archive',NativeMemoryTests,person_correction_crash)
run('native_idea_type_filter',NativeMemoryTests,native_idea_filter)
run('native_configuration_revocation',MemoryDelegationTests,malformed_and_revoked)

def concurrent_native_processes(test):
    from concurrent.futures import ThreadPoolExecutor
    def add(number):
        return test.call([{'name':'add','item':{'type':'memory','actor':'principal','content':f'RULE: synthetic concurrent native fact {number}'}}])[0]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(add,range(4)))
    found=test.fixture.memory.recall(OWNER,'concurrent native fact')
    assert all(result['ok'] for result in results),results
    assert len(found)==4,found
    return {'all_committed':True,'record_count':len(found),'contents':[row['content'] for row in found]}

def schema_rejection(test):
    import sqlite3
    test.fixture.remember('RULE: synthetic schema fact','schema','principal')
    with sqlite3.connect(test.fixture.memory.database) as connection:
        connection.execute('PRAGMA user_version=1')
    result=test.call([{'name':'read','path':str(test.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md')}])
    with sqlite3.connect(test.fixture.memory.database) as connection:
        version=connection.execute('PRAGMA user_version').fetchone()[0]
    assert version==1 and not result[0]['ok']
    return {'result':result,'version_after':version}

run('parallel_native_adds_preserve_acknowledged_facts',MemoryDelegationTests,concurrent_native_processes)
run('schema_one_is_refused_without_migration',MemoryDelegationTests,schema_rejection)
