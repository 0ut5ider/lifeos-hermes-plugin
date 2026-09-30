# ABOUTME: Checks project audience admission and private archive duplicate handling.
# ABOUTME: Runs only against disposable synthetic native fixtures.
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone
import json, sys
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'tests'))
from test_memory_native import NativeMemoryTests, OWNER
from test_memory_delegation import MemoryDelegationTests

def run(name, cls, callback):
    f=cls(); f.setUp()
    try: print(json.dumps({'case':name,'result':callback(f)},sort_keys=True),flush=True)
    finally: f.doCleanups()

def restricted_project_history(f):
    scope=replace(OWNER,projects=('lab',))
    saved=f.fixture.memory.remember(OWNER,category='project',content='Synthetic other-project confidential marker',title='Other project',project='other',request_id='other')
    config=f.configuration.load()
    config['destinations']['chat-a:200']['projects']=['lab']
    f.configuration.save(config)
    prompt=f.call([{'name':'review_prompt','exchanges':[{'ts':datetime.now(timezone.utc).isoformat(),'user':'Synthetic other-project confidential marker','assistant':'Keep the other project record.'}]}])[0]
    return {'saved':saved,'scoped_recall':f.fixture.memory.recall(scope,'other-project confidential'),'prompt':prompt}

def private_duplicate(f):
    project=replace(OWNER,read=('project',),write=('project',),projects=('lab',),writer='local:project')
    item={'type':'knowledge','entity_type':'person','name':'Fictional Person','content':'Synthetic identical archive fact'}
    private=f.memory.native_add(OWNER,item,request_id='private',project='lab')
    denied=f.memory.native_add(project,{**item,'content':'Synthetic denied entity write'},request_id='denied',project='lab')
    public=f.memory.remember(project,category='project',content=item['content'],title='Public project note',project='lab',request_id='public')
    result={'private':private,'denied_native_entity_write':denied,'public_save':public,'scoped_recall':f.memory.recall(project,'identical archive fact')}
    if 'reference' in public: result['get_public']=f.memory.get(project,public['reference'])
    original=f.memory.remember(project,category='project',content='Synthetic initial public fact',title='Public project note',project='lab',request_id='public-initial')
    corrected=f.memory.correct(project,original['reference'],item['content'],'public-correct')
    result['correct_public']=corrected
    result['old_public_after_correction']=f.memory.get(project,original['reference'])
    result['corrected_public_get']=f.memory.get(project,corrected['reference'])
    return result

run('all_categories_but_restricted_project_history',MemoryDelegationTests,restricted_project_history)
run('project_save_collides_with_private_entity',NativeMemoryTests,private_duplicate)
