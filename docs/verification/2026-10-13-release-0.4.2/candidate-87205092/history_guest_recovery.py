# ABOUTME: Prepares synthetic archived Atlas groups for whole-guest recovery verification.
# ABOUTME: Verifies exact restored bytes and preserves later edits without using personal data.
from contextlib import closing
from dataclasses import asdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

parser=argparse.ArgumentParser()
parser.add_argument('action',choices=('prepare','verify'))
parser.add_argument('package',type=Path)
args=parser.parse_args()
os.umask(0o077)
base=Path('/home/lifeos-hermes');package=args.package.resolve()
sys.path[:0]=[str(package),str(package/'hermes')]
os.environ.update(PATH=str(base/'.local/bin')+':'+str(Path(sys.executable).parent)+':/usr/local/bin:/usr/bin:/bin',
    PYTHONDONTWRITEBYTECODE='1')
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_access import NativeMemory,MemoryUnavailable
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folder=base/'deployment/history-recovery-0.4.2-87205092'
live_root=Path(json.loads((base/'.hermes/lifeos-memory.json').read_text())['root'])
results=[]
for case in ('baseline','interrupted','later-edit'):
    selected=folder/case
    if args.action=='prepare':
        assert not selected.exists();selected.mkdir(parents=True,mode=0o700)
        home=selected/'home';root=home/'.claude';data=home/'.config/LIFEOS/USER';profile=home/'.hermes'
        (root/'LIFEOS').mkdir(parents=True);(data/'MEMORY').mkdir(parents=True);profile.mkdir()
        (root/'LIFEOS/USER').symlink_to(data,target_is_directory=True)
        (root/'LIFEOS/MEMORY').symlink_to(data/'MEMORY',target_is_directory=True)
        for name in ('TOOLS','ATLAS','PULSE'):(root/'LIFEOS'/name).symlink_to(live_root/'LIFEOS'/name,target_is_directory=True)
        (root/'hooks').symlink_to(live_root/'hooks',target_is_directory=True)
        (root/'settings.json').write_text('{}')
        for parent,name in [('PRINCIPAL','PRINCIPAL_MEMORY.md'),('DIGITAL_ASSISTANT','DA_MEMORY.md')]:
            p=data/parent/name;p.parent.mkdir();p.write_text('---\nlast_updated_by: synthetic\n---\n<!-- BEGIN ENTRIES -->\n<!-- END ENTRIES -->\n')
        (data/'GEAR.md').write_text('## Computing\n| **Laptop** | Synthetic Archive Recovery Device | daily |\n')
        (data/'PROJECTS.md').write_text('| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n| Synthetic Archive Recovery | /synthetic/recovery | recovery.example.invalid | local |\n')
        conf=MemoryConfiguration(profile/'lifeos-memory.json')
        conf.save({'version':1,'root':str(root),'principal':'synthetic-owner','ownership_enabled':False,'sharing_enabled':False,
            'accounts':{'terminal:'+str(os.getuid()):'synthetic-owner'},
            'destinations':{'terminal:'+str(profile):{'visibility':'private','participants':['synthetic-owner'],
                'read':['principal','assistant','project'],'write':['principal','assistant','project'],
                'projects':['*'],'model_routes':['local']}},'clients':{}})
        context=SessionContext('terminal',str(os.getuid()),str(profile),'private',('synthetic-owner',),'local','history-recovery-'+case)
        (data/'CONFIG').mkdir()
        connector=data/'CONFIG/memory-access.json'
        connector.write_text(json.dumps({'version':1,'command':[sys.executable,str(package/'lifeos_hook_bridge/memory_rpc.py'),'--configuration',str(conf.path)]}));connector.chmod(0o600)
        service=MemoryService(conf)
        assert service.native(context,'atlas_sync',{'collectors':['gear','projects'],'scope':'full'})['ok']
        def seed():
            program='import {Store} from '+json.dumps(str(root/'LIFEOS/ATLAS/Store.ts'))+';const s=new Store();for(let i=0;i<64;i++)s.applyRun("gear","full",{complete:false,assets:[],edges:[]});s.db.exec("PRAGMA wal_checkpoint(TRUNCATE)");s.db.exec("PRAGMA journal_mode=DELETE");s.close();'
            r=subprocess.run([str(base/'.local/bin/bun'),'--no-install','-e',program],env=dict(os.environ,HOME=str(home),LIFEOS_MEMORY_INTERNAL='1'),capture_output=True,text=True,timeout=60)
            assert (r.returncode,r.stdout,r.stderr)==(0,'','')
        seed()
        receipt=service.native(context,'atlas_sync',{'collectors':['gear','projects'],'scope':'full'})
        assert receipt['ok'] and receipt['history']['archive_id'],receipt
        memory=NativeMemory(root)
        if case!='baseline':seed()
        original={str(p):{'sha256':sha(p),'mode':p.stat().st_mode & 0o777} for p in home.rglob('*') if p.is_file() and not p.is_symlink()}
        archive_ids=[p.name for p in (home/'.local/state/lifeos/atlas/history').iterdir()]
        if case!='baseline':
            r=subprocess.run([sys.executable,'-B',str(package/'tests/memory_atlas_retention_process.py'),str(conf.path),json.dumps(asdict(context)),'atlas.db'],
                env=dict(os.environ,HOME=str(home),HERMES_HOME=str(profile),PYTHONPATH=str(package)+':'+str(package/'hermes')),capture_output=True,text=True,timeout=90)
            assert (r.returncode,r.stdout,r.stderr)==(73,'',''),r
            assert memory.transaction.journal.exists()
        if case=='later-edit':
            journal=json.loads(memory.transaction.journal.read_text())
            name=next(row['path'] for row in journal['copies'] if row['path'].endswith('/manifest.json'))
            archive=memory._publication_path(name)
            value=json.loads(archive.read_text());value['sources']['synthetic']='Later owner edit';archive.write_text(json.dumps(value))
        captured={str(p):{'sha256':sha(p),'mode':p.stat().st_mode & 0o777} for p in home.rglob('*') if p.is_file() and not p.is_symlink()}
        prepared={'case':case,'home':str(home),'configuration':str(conf.path),'context':asdict(context),'original':original,
            'captured':captured,'archive_ids_before':archive_ids,'known_archive_id':receipt['history']['archive_id']}
        (selected/'prepared.json').write_text(json.dumps(prepared,indent=2)+'\n')
        results.append({'case':case,'files':len(captured),'archives':len(list((home/'.local/state/lifeos/atlas/history').iterdir())),
            'journal_present':memory.transaction.journal.exists()})
    else:
        prepared=json.loads((selected/'prepared.json').read_text())
        assert all(Path(name).is_file() and sha(Path(name))==row['sha256'] and Path(name).stat().st_mode & 0o777==row['mode']
            for name,row in prepared['captured'].items()),'The actual restore changes fixture bytes or modes'
        conf=MemoryConfiguration(Path(prepared['configuration']));context=SessionContext(**prepared['context'])
        root=Path(conf.load()['root']);memory=NativeMemory(root)
        refused=False
        if case=='later-edit':
            try:
                with memory._transaction():pass
            except MemoryUnavailable as e:
                assert 'later artifact edit' in str(e);refused=True
            assert refused and memory.transaction.journal.exists()
            assert all(sha(Path(name))==row['sha256'] for name,row in prepared['captured'].items())
        else:
            with memory._transaction():pass
            assert not memory.transaction.journal.exists()
            assert all(sha(Path(name))==row['sha256'] for name,row in prepared['original'].items()
                if name.endswith(('atlas.db','snapshot.json','manifest.json')))
            history=root.parent/'.local/state/lifeos/atlas/history'
            assert sorted(p.name for p in history.iterdir() if any(p.iterdir()))==sorted(prepared['archive_ids_before'])
            result=MemoryService(conf).native(context,'atlas_history',{'archive_id':prepared['known_archive_id'],'table':'sync_run','offset':0})
            assert result['ok'] and result['rows'],result
        results.append({'case':case,'status':'PASS','restored_files':len(prepared['captured']),
            'later_edit_refused':refused,'archive_and_live_group_verified':True})
report={'status':'PASS','action':args.action,'version':json.loads((package/'DAILY-CANDIDATE.json').read_text())['version'],
    'cases':results,'personal_data_used':False,'live_store_modified':False}
(folder/(args.action+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
