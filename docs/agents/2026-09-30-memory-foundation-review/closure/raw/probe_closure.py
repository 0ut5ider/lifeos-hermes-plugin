# ABOUTME: Verifies heading recall and scoped native BM25 behavior with synthetic facts.
# ABOUTME: Checks same-process cache boundaries against the actual managed native retriever.
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_native import NativeMemoryTests,OWNER,READER,SOURCE

test=NativeMemoryTests()
test.setUp()
try:
    content='Synthetic first paragraph\n## Appended experiment notes\nSynthetic second paragraph'
    saved=test.remember(content,'heading-content')
    found=test.memory.recall(OWNER,'Synthetic')
    assert saved['status']=='committed' and found[0]['content']==content
    print(json.dumps({'case':'exact_heading_probe','saved':saved,'recall':found}))
    test.remember('RULE: synthetic denied principal marker','private','principal')
    other=test.memory.remember(OWNER,category='project',content='Synthetic denied other project marker',
                               title='Synthetic lab routing',project='other',request_id='other')
    first=test.remember('Synthetic superseded archive marker','superseded')
    replacement=test.memory.correct(OWNER,first['reference'],'Synthetic allowed correction marker','correction')
    found=test.memory.recall(READER,'synthetic')
    assert all(row['category']=='project' and row['project']=='lab' for row in found)
    text=json.dumps(found)
    assert 'denied' not in text and 'superseded archive' not in text
    assert any(row['reference']==replacement['reference'] for row in found)
    print(json.dumps({'case':'authorized_current_corpus','recall':found}))
    script=test.home/'retrieval-cache.ts'
    script.write_text('''// ABOUTME: Tests native supplied-corpus isolation within one Bun process.
// ABOUTME: Uses only synthetic notes under the temporary fixture root.
const retriever=await import(process.argv[2]+"/LIFEOS/TOOLS/MemoryRetriever.ts");
const note=(id:string)=>({filePath:id,frontmatter:{type:"knowledge",title:id},body:"synthetic "+id,wordCount:2,noteClass:"knowledge"});
const ordinary=retriever.getRelevantContext("synthetic");
const first=retriever.getRelevantContext("synthetic",{corpus:[note("FIRST_ALLOWED")]});
const second=retriever.getRelevantContext("synthetic",{corpus:[note("SECOND_ALLOWED")]});
const empty=retriever.getRelevantContext("synthetic",{corpus:[]});
const ordinaryAgain=retriever.getRelevantContext("synthetic");
process.stdout.write(JSON.stringify({ordinary,first,second,empty,ordinaryAgain}));
''')
    env=dict(os.environ,HOME=str(test.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
    result=subprocess.run(['bun','--no-install',str(script),str(test.root)],capture_output=True,text=True,
                          env=env,cwd=test.root,timeout=30)
    assert result.returncode==0,result.stderr
    result=json.loads(result.stdout)
    assert [x['path'] for x in result['first']['results']]==['FIRST_ALLOWED']
    assert [x['path'] for x in result['second']['results']]==['SECOND_ALLOWED']
    assert result['empty']['results']==[] and result['empty']['totalSearched']==0
    assert result['ordinaryAgain']['results']==result['ordinary']['results']
    assert result['ordinaryAgain']['cached']
    assert all(not result[key]['cached'] for key in ('first','second','empty'))
    print(json.dumps({'case':'same_process_cache_isolation','result':result}))
finally:
    test.doCleanups()
