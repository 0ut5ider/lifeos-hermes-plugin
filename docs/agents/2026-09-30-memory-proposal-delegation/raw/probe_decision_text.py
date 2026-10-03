# ABOUTME: Checks private decision notes and durable receipt contents in real native proposals.
# ABOUTME: Uses only temporary synthetic targets and proposal text.
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
f=MemoryProposalTests();f.setUp()
try:
 item=f.item('Always preserve the synthetic receipt marker.')
 saved=f.enqueue('note-source',item)
 note='Applied in a synthetic hook. <private>PRIVATE-NOTE-MARKER</private>'
 result=f.memory.decide_proposal(f.scope,saved['receipt']['proposal_reference'],'applied_elsewhere','private-note',note=note)
 with f.memory._transaction() as db:
  receipt=db.execute('SELECT receipt FROM operations WHERE request_id=?',('private-note',)).fetchone()[0]
 rows=f.memory.review_proposals(f.scope,include_resolved=True)
 print(json.dumps({'result':result,'resolved_rows':rows,'receipt_contains_edit':item['edit'] in receipt,'receipt_contains_private_note':'PRIVATE-NOTE-MARKER' in receipt,'queue_contains_private_note':'PRIVATE-NOTE-MARKER' in Path(saved['path']).read_text()}),flush=True)
finally:f.doCleanups()
