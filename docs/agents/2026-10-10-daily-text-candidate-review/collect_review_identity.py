# ABOUTME: Captures the exact reviewed candidate and immutable patch/source identities.
# ABOUTME: Saves cited source lines and inventory without changing shared source files.
from pathlib import Path
import subprocess, json, hashlib, runpy
ROOT=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin');OUT=Path(__file__).parent
from lifeos_hook_bridge.install_source import HERMES_PATCHES,LIFEOS_PATCHES
HEAD='bf53c16dd23d72c9824843cbb85f31db5a48e723';BASE='c0b26bd57d6abf5364f60e3c33c6b3bea53c5ab8'
def git(*args):
    r=subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True)
    return {'command':['git',*args],'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
patches=[{'name':n,'sha256':digest(ROOT/'patches'/n),'packaged_sha256':digest(ROOT/'lifeos_hook_bridge/patches'/n)} for n in (*HERMES_PATCHES,*LIFEOS_PATCHES)]
prepared=Path('/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed')
manifests={name:json.loads((prepared/name/(name+'-source-manifest.json')).read_text()) for name in ('lifeos','hermes')}
reused=Path('/home/outsider/.cache/lifeos-daily-text-20261007/content-response-first/lifeos/LifeOS/install')
comparison=[]
for name in ('LIFEOS/TOOLS/lib/MemoryAccess.ts','LIFEOS/TOOLS/SessionHarvester.ts','LIFEOS/TOOLS/ProposalGC.ts','LIFEOS/TOOLS/KnowledgeHarvester.ts','LIFEOS/PULSE/modules/algorithm-tab.ts','LIFEOS/PULSE/modules/user-index.ts','LIFEOS/PULSE/modules/content.ts'):
    a=prepared/'lifeos/LifeOS/install'/name;b=reused/name
    comparison.append({'relative':name,'prepared_sha256':digest(a),'test_source_sha256':digest(b),'equal':a.read_bytes()==b.read_bytes()})
registry=runpy.run_path(str(ROOT/'scripts/prepare_sources.py'))['SOURCES']
value={'date':'2026-10-10','expected_head':HEAD,'base':BASE,'head':git('rev-parse','HEAD'),
    'tracked_status':git('status','--short','--untracked-files=no'),
    'diff_check':git('diff','--check',BASE,HEAD,'--','lifeos_hook_bridge','scripts','tests','patches'),
    'changed_runtime_inventory':git('diff','--name-status',BASE,HEAD,'--','lifeos_hook_bridge','scripts','tests','patches'),
    'patches':patches,'registry_equal':registry['hermes']['patches']==HERMES_PATCHES and registry['lifeos']['patches']==LIFEOS_PATCHES,
    'prepared_manifests':manifests,'native_behavior_source_comparisons':comparison}
(OUT/'review-identity.json').write_text(json.dumps(value,indent=2))
with (OUT/'finding-source-lines.txt').open('w') as f:
    for name,begin,end in [('lifeos_hook_bridge/memory_session_harvest.py',139,183),('lifeos_hook_bridge/memory_proposal_gc.py',88,106),('lifeos_hook_bridge/memory_knowledge_harvest.py',232,257),('lifeos_hook_bridge/memory_algorithm_edit.py',169,207),('lifeos_hook_bridge/memory_access.py',123,143),('lifeos_hook_bridge/memory_access.py',348,382),('lifeos_hook_bridge/memory_transaction.py',191,229)]:
        f.write('\n'+name+'\n');lines=(ROOT/name).read_text().splitlines()
        for i in range(begin-1,min(end,len(lines))):f.write(str(i+1)+': '+lines[i]+'\n')
print(json.dumps({'head':value['head']['stdout'].strip(),'tracked_status':value['tracked_status']['stdout'],'patch_count':len(patches),'patches_equal':all(p['sha256']==p['packaged_sha256'] for p in patches),'registries_equal':value['registry_equal'],'native_comparisons':comparison,'diff_check_exit':value['diff_check']['exit_code']},indent=2))
