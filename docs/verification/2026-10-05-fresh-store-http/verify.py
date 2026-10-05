# ABOUTME: Verifies the authenticated preparation evidence and its recorded source files.
# ABOUTME: Rejects modified artifacts or a failed native HTTP test marker.
import hashlib
import json
from pathlib import Path


bundle=Path(__file__).resolve().parent
project=bundle.parents[2]
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
artifacts=json.loads((bundle/'artifact-hashes.json').read_text())
sources=json.loads((bundle/'source-hashes.json').read_text())
for name,expected in artifacts.items():
    if digest(bundle/name)!=expected:raise ValueError('An evidence artifact changes: '+name)
for name,expected in sources.items():
    if digest(project/name)!=expected:raise ValueError('A recorded source changes: '+name)
if (bundle/'http.done').read_text().strip()!='0':raise ValueError('The native HTTP test does not pass')
print(json.dumps({'artifacts':len(artifacts),'sources':len(sources)}))
