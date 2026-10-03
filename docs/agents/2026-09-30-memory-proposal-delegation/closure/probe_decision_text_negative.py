# ABOUTME: Checks rejection of private resolution notes and metadata-only decision receipts.
# ABOUTME: Reads proposal bodies only from verified native resolved history in temporary fixtures.
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_proposals import MemoryProposalTests
f=MemoryProposalTests();f.setUp()
try:
 item=f.item('Always preserve the synthetic receipt marker.');saved=f.enqueue('note-source',item);ref=saved['receipt']['proposal_reference']
 note='Applied in a synthetic hook. <private>PRIVATE-NOTE-MARKER</private>'
 rejected=f.memory.decide_proposal(f.scope,ref,'applied_elsewhere','private-note',note=note)
 assert rejected['status']=='rejected'
 with f.memory._transaction() as db:bad_receipt=db.execute('SELECT receipt FROM operations WHERE request_id=?',('private-note',)).fetchone()
 assert bad_receipt is None;assert 'PRIVATE-NOTE-MARKER' not in Path(saved['path']).read_text()
 valid_note='Applied in a synthetic enforcement hook.'
 result=f.memory.decide_proposal(f.scope,ref,'applied_elsewhere','valid-note',note=valid_note)
 assert result['status']=='committed' and 'row' not in result
 with f.memory._transaction() as db:receipt=db.execute('SELECT receipt FROM operations WHERE request_id=?',('valid-note',)).fetchone()[0]
 assert all(body not in receipt for body in (item['edit'],item['rationale'],valid_note))
 rows=f.memory.review_proposals(f.scope,include_resolved=True)
 assert rows[0]['resolution_note']==valid_note and rows[0]['edit']==item['edit']
 assert f.memory.decide_proposal(f.scope,ref,'applied_elsewhere','valid-note',note=valid_note)==result
 print(json.dumps({'private_result':rejected,'private_receipt_created':bad_receipt is not None,'private_note_queued':False,'valid_result':result,'durable_receipt':json.loads(receipt),'resolved_rows':rows,'identical_retry':True}),flush=True)
finally:f.doCleanups()
