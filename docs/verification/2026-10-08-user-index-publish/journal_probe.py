# ABOUTME: Observes synthetic index source metadata around an actual journaled publication.
# ABOUTME: Records directory entries and source digests without changing the publication or reading real personal data.
import hashlib
import json
from pathlib import Path
from test_memory_user_index_publish import MemoryUserIndexPublishTests
import lifeos_hook_bridge.memory_user_index_publish as publisher
from lifeos_hook_bridge.memory_service import MemoryService

observations = []
original = publisher._collect

def observe(*args):
    sources, fingerprints = original(*args)
    observations.append({'sources_digest': hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        'directories': {row[0]: row[1] for row in fingerprints if len(row)==2}})
    return sources, fingerprints

publisher._collect = observe
fixture = MemoryUserIndexPublishTests('test_owner_cli_publishes_a_private_index_and_preserves_source_bytes')
try:
    fixture.setUp()
    result = MemoryService(fixture.configuration).native(fixture.fixture.context, 'user_index',
        {'query': None, 'publish_index': True, 'request_id': 'synthetic-journal-probe'})
    output = {'ok': result.get('ok'), 'message': result.get('message'), 'observations': observations}
    Path(__file__).with_name('journal-probe.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'ok': output['ok'], 'message': output['message'],
        'source_digests': [item['sources_digest'] for item in observations],
        'state_entries': [item['directories'].get('LIFEOS/USER/MEMORY/STATE') for item in observations]}))
finally:
    fixture.doCleanups()
