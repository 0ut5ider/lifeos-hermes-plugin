# ABOUTME: Tests native proposal decisions when a configured connector becomes a dangling symlink.
# ABOUTME: Uses real Bun RPC controls and a disposable native target with approval revoked.
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposal_delegation import MemoryProposalDelegationTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
f=MemoryProposalDelegationTests();f.setUp()
try:
 saved=f.fixture.enqueue();ref=saved['receipt']['proposal_reference']
 f.value['destinations']['chat-a:200']['proposals']=[];MemoryConfiguration(f.config).save(f.value)
 denied=f.call('accept',id=ref['id'])
 connector=f.root/'LIFEOS/USER/CONFIG/memory-access.json';connector.unlink();connector.symlink_to(f.fixture.fixture.home/'missing-connector.json')
 accepted=f.call('accept',id=ref['id'])
 with f.fixture.memory._transaction() as db:record=dict(db.execute('SELECT * FROM proposals WHERE id=?',(ref['id'],)).fetchone())
 print(json.dumps({'before_broken_connector':denied,'after_broken_connector':accepted,'target_contains_edit':f.fixture.item()['edit'] in f.fixture.target.read_text(),'sqlite_status':record['status'],'connector_is_symlink':connector.is_symlink(),'connector_exists':connector.exists()}),flush=True)
finally:f.doCleanups()
