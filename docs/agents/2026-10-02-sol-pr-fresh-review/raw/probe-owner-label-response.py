# ABOUTME: Checks private source labels through currently enabled owner preferences.
# ABOUTME: Keeps memory ownership and external sharing disabled throughout the probe.
import json, pathlib, os
from test_memory_native import NativeMemoryTests, OWNER
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
OUT=pathlib.Path(__file__).resolve().parent
fixture=NativeMemoryTests();fixture.temporary_parent=str(OUT/'fixture-home/tmp');fixture.setUp()
try:
    marker='SYNTHETIC_OWNER_PRIVATE_LABEL'
    relative='LIFEOS/MEMORY/KNOWLEDGE/Research/<private>'+marker+'.md'
    path=fixture.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('---\ntitle: Safe Synthetic Note\ntype: research\ncreated: 2026-10-02T00:00:00Z\nupdated: 2026-10-02T00:00:00Z\n---\n\nSafeSyntheticCurrentBody\n')
    (fixture.root/'LIFEOS/PULSE').symlink_to(pathlib.Path(os.environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS/PULSE')
    profile=fixture.home/'hermes';profile.mkdir(mode=0o700)
    configuration=MemoryConfiguration(profile/'lifeos-memory.json')
    configuration.save({'version':1,'root':str(fixture.root),'principal':'owner','ownership_enabled':False,'sharing_enabled':False,
        'accounts':{'dashboard:synthetic-owner':'owner'},'destinations':{},'clients':{}})
    prefs=MemoryPreferences(configuration.path,fixture.root,fixture.home/'.ssh/authorized_keys',pathlib.Path(__import__('sys').executable),OUT/'synthetic-unused-program')
    preview=prefs.preview_adoption(account='dashboard:synthetic-owner')
    adopted=prefs.adopt({'signature':preview['signature'],'projects':{relative:'lab'},'request_id':'adopt-private-owner-label'},account='dashboard:synthetic-owner')
    knowledge,binding=prefs.knowledge_response('/api/knowledge',account='dashboard:synthetic-owner')
    searched=prefs.review('lifeos_memory_search',{'query':'SafeSyntheticCurrentBody'},account='dashboard:synthetic-owner')
    print(json.dumps({'ownership_enabled':configuration.load()['ownership_enabled'],'sharing_enabled':configuration.load()['sharing_enabled'],
        'adopted':adopted,'knowledge_response':knowledge,'search_response':searched,'private_marker_in_knowledge':marker in json.dumps(knowledge),
        'private_marker_in_owner_search':marker in json.dumps(searched)},indent=2))
finally:fixture.doCleanups()
