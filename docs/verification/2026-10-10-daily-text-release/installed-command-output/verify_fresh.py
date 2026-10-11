# ABOUTME: Prepares a new native store on the development guest without selecting it.
# ABOUTME: Verifies empty personal views, native graph initialization, and exact retained templates.
import importlib
import json
import os
from pathlib import Path
import sys

stage=Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package=Path(__file__).resolve().parents[1]/'package'
prepared=json.loads((stage/'applications-prepared.json').read_text())
profile=Path(prepared['profile'])
sys.path[:0]=[str(profile/'plugins'),str(stage/'package/hermes')]
module=lambda name:importlib.import_module('lifeos-hook-bridge.'+name)
configuration=module('memory_service').MemoryConfiguration(profile/'lifeos-memory.json')
before=configuration.path.read_bytes()
os.environ.update(PATH='/home/lifeos-hermes/.local/bin:/usr/bin:/bin')
result=module('fresh_store').FreshStore(configuration).prepare(package/'lifeos',
    principal_name='Adrian',assistant_name='Cerebo',account='dashboard:basic:acceptance-owner')
root=Path(result['installed']);user=Path(result['data'])
os.environ.update(HOME=str(root.parent),HERMES_HOME=str(profile),
    PATH='/home/lifeos-hermes/.local/bin:/usr/bin:/bin',BUN_CONFIG_NO_AUTO_INSTALL='1')
memory=module('memory_access').NativeMemory(root)
scope=module('memory_preferences').MemoryPreferences._owner_scope(configuration.load())
assert result['active_facts']==0
assert not result['ownership_enabled'] and not result['sharing_enabled'] and not result['services_started']
assert configuration.path.read_bytes()==before
assert len(result['omitted_personal_templates'])==3
for relative in result['empty_personal_templates']+result['omitted_personal_templates']:
    retained=root.parent.parent/'template-originals'/relative
    assert retained.read_bytes()==(package/'lifeos/LifeOS/install/USER'/relative).read_bytes()
    assert retained.stat().st_mode & 0o077==0
views={name:module(name).view(memory,scope) for name in
    ('memory_life_finances','memory_life_health','memory_life_business','memory_life_work')}
for name,response in views.items():
    assert response['status']==200,(name,response)
    assert '(sample)' not in json.dumps(response) and 'Sample ' not in json.dumps(response),(name,response)
brief=module('memory_morning_brief').run(memory,scope)
assert 'Your top goals' not in brief['stdout'] and '(sample)' not in brief['stdout']
graph=module('memory_atlas_sync').run(memory,scope,['gear','projects'],'full',check_current=lambda:None)
assert graph['ok'] is True,graph
native_graph=module('memory_atlas').view(memory,scope)
assert not native_graph['body']['assets'],native_graph
assert configuration.path.read_bytes()==before
report={'status':'PASS','names':result['names'],'fresh_store_root':str(root),
    'active_facts':0,'empty_personal_templates':result['empty_personal_templates'],
    'omitted_personal_templates':result['omitted_personal_templates'],'originals_verified':True,
    'views':views,'morning_brief':brief,'empty_atlas':native_graph,
    'ownership_enabled':False,'sharing_enabled':False,'services_started':False,
    'selected_profile_preserved':True,'live_profile_changed':False}
(stage/'release-fresh-store.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
