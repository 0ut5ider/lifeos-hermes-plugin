# ABOUTME: Checks a broken native upgrade sidecar symlink before governed publication.
# ABOUTME: The outside target is synthetic and remains inside the disposable fixture home.
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
f=MemoryProposalTests();f.setUp()
try:
 upgrades=f.fixture.root/'LIFEOS/MEMORY/UPGRADES';upgrades.mkdir(parents=True)
 outside=f.fixture.home/'synthetic-outside-user-boundary.json'
 state=upgrades/'.state.json';state.symlink_to(outside)
 result=f.enqueue('broken-link',f.item('SyntheticLab must use a dedicated deployment checklist.'))
 try:after=f.memory.review_proposals(f.scope)
 except Exception as error:after={'error':type(error).__name__,'message':str(error)}
 print(json.dumps({'result':result,'outside_created':outside.exists(),'outside_content':outside.read_text() if outside.exists() else None,'state_symlink':state.is_symlink(),'after_recovery':after,'journal_exists':f.memory.transaction.journal.exists()}),flush=True)
finally:f.doCleanups()
