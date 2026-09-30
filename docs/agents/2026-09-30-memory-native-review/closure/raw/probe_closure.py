# ABOUTME: Verifies duplicate visibility classes and current native content validation.
# ABOUTME: Uses disposable synthetic fixtures and actual native writer operations.
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import NativeMemoryTests, OWNER, READER

def run(name,callback):
    f=NativeMemoryTests(); f.setUp()
    try: print(json.dumps({'case':name,'result':callback(f)},sort_keys=True),flush=True)
    finally: f.doCleanups()

def owner_visibility(f):
    item={'type':'knowledge','entity_type':'person','name':'Fictional private person','content':'Synthetic matching visibility fact'}
    private=f.memory.native_add(OWNER,item,request_id='private',project='lab')
    public=f.memory.remember(OWNER,category='project',content=item['content'],title='Public visibility',project='lab',request_id='public')
    assert public['status']=='committed' and public['reference']!=private['receipt']['reference']
    assert f.memory.get(READER,public['reference'])['status']=='ok'
    assert f.memory.get(READER,private['receipt']['reference'])['status']=='rejected'
    return {'private':private,'public':public,'reader_public':f.memory.get(READER,public['reference'])}

def private_correction(f):
    public=f.remember('Synthetic shared matching correction','public')
    private=f.memory.native_add(OWNER,{'type':'knowledge','entity_type':'company','name':'Fictional company','content':'Synthetic original private correction'},request_id='private',project='lab')
    corrected=f.memory.correct(OWNER,private['receipt']['reference'],'Synthetic shared matching correction','correct')
    assert corrected['status']=='committed' and corrected['reference']!=public['reference']
    assert f.memory.get(READER,corrected['reference'])['status']=='rejected'
    assert f.memory.get(OWNER,corrected['reference'])['status']=='ok'
    return {'public':public,'corrected_private':corrected,'reader_corrected_private':f.memory.get(READER,corrected['reference'])}

def changed_native_duplicate(f):
    first=f.remember('Synthetic current duplicate marker','first')
    path=next((f.root/'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    path.write_text(path.read_text().replace('Synthetic current duplicate marker','Synthetic mutated duplicate marker'))
    result=f.remember('Synthetic current duplicate marker','retry-new-request')
    assert result['status']=='conflict',result
    assert 'Synthetic mutated duplicate marker' in path.read_text()
    return {'first':first,'duplicate_result':result}

run('owner_preserves_public_private_visibility',owner_visibility)
run('private_correction_does_not_merge_public_duplicate',private_correction)
run('duplicate_requires_current_native_content',changed_native_duplicate)
