# ABOUTME: Compares managed and standalone sample selection after an existing cursor.
# ABOUTME: Uses real native writes and unchanged cursor bytes in a disposable owner fixture.
import json
from test_memory_delta import MemoryDeltaTests
f=MemoryDeltaTests();f.setUp()
try:
 f.remember('Synthetic first sample alpha','first')
 f.remember('Synthetic second sample beta','second')
 first=f.call(standalone=True)
 cursor=f.obs/'memory-delta-cursor.json';before=cursor.read_bytes()
 f.remember('Synthetic later sample gamma','third')
 managed=f.call(standalone=True)
 cursor.write_bytes(before)
 (f.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
 unmanaged=f.call(standalone=True)
 print(json.dumps({'first':first,'managed_followup':managed,'unmanaged_same_followup':unmanaged,'managed_has_new_sample':'Synthetic later sample gamma' in managed,'unmanaged_has_new_sample':'Synthetic later sample gamma' in unmanaged}))
finally:f.doCleanups()
