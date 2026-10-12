# ABOUTME: Reviews fixed Atlas snapshot and graph sources under the actual daily owner policy.
# ABOUTME: Preserves source bytes and timestamps while refusing private and retired content.
import importlib
import json
import os
from pathlib import Path
import sys

os.umask(0o077)
assert os.getuid() == 1000
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
sys.path.insert(0, str(profile / 'plugins'))
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json').load()
assert configuration['ownership_enabled'] and not configuration['sharing_enabled']
selected = json.loads((profile / 'integration-release.json').read_text())
assert selected['version'] == '0.3.1'
root = Path(configuration['root'])
memory = module('memory_access').NativeMemory(root, profile=profile)
atlas = module('memory_atlas')
paths = [path for path in (atlas.SNAPSHOT, atlas.DATABASE, atlas.CACHE)
    if atlas.source_path(memory, path).is_file()]
preferences = module('memory_preferences').MemoryPreferences(profile / 'lifeos-memory.json', root,
    Path(sys.executable), profile / 'plugins/lifeos-hook-bridge/memory_mcp.py')
snapshot = preferences.preview_sources(paths, account='terminal:1000')
assert all(row['accepted'] for row in snapshot['sources']), 'The owner policy refuses an Atlas launch source'
before = {name: (atlas.source_path(memory, name).read_bytes(), atlas.source_path(memory, name).stat().st_mtime_ns)
    for name in paths}
result = preferences.approve_sources({'paths': paths, 'signature': snapshot['signature']}, account='terminal:1000')
assert result['status'] in {'committed', 'unchanged'}, result
assert all((atlas.source_path(memory, name).read_bytes(), atlas.source_path(memory, name).stat().st_mtime_ns) == value
    for name, value in before.items())
report = {'status': 'PASS', 'sources': paths, 'review_status': result['status'],
    'bytes_and_timestamps_preserved': True, 'contents_exported': False}
output = home / 'deployment' / ('release-' + selected['version'] + '-' + selected['commit'][:8])
(output / 'atlas-launch-source-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
