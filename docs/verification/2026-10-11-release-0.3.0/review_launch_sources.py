# ABOUTME: Reviews fixed daily operational sources under the current local owner policy.
# ABOUTME: Preserves source bytes and withholds approval for private or retired content.
import argparse
import importlib
import json
import os
from pathlib import Path
import re
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
os.umask(0o077)
assert os.getuid() == 1000, 'Launch review selects only the daily guest owner'
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
sys.path.insert(0, str(profile / 'plugins'))
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json').load()
assert configuration['ownership_enabled'] and not configuration['sharing_enabled']
root = Path(configuration['root'])
selected = json.loads((profile / 'integration-release.json').read_text())
assert selected['version'] == '0.3.1'
paths = ['LIFEOS/USER/CONDUIT/config.json', 'LIFEOS/USER/CONDUIT/state.json',
    'LIFEOS/MEMORY/STATE/work-events.jsonl#conduit-pending', 'LIFEOS/USER/GEAR.md', 'LIFEOS/USER/PROJECTS.md']
events = root / 'LIFEOS/USER/CONDUIT/events'
if events.is_dir():
    paths += [str(path.relative_to(root)) for path in sorted(events.iterdir())
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.jsonl', path.name)]
paths = [path for path in paths if (root / path.split('#', 1)[0]).is_file()]
preferences = module('memory_preferences').MemoryPreferences(profile / 'lifeos-memory.json', root,
    Path(sys.executable), profile / 'plugins/lifeos-hook-bridge/memory_mcp.py')
snapshot = preferences.preview_sources(paths, account='terminal:1000')
accepted = [row['path'] for row in snapshot['sources'] if row['accepted']]
refused = [row['path'] for row in snapshot['sources'] if not row['accepted']]
report = {'status': 'PREVIEW', 'sources': len(paths), 'accepted': len(accepted), 'refused': refused,
    'applied': False, 'bytes_preserved': True, 'timestamps_preserved': True}
if args.apply:
    assert not refused, 'The launch review refuses private or retired sources'
    before = {path: ((root / path.split('#', 1)[0]).read_bytes(), (root / path.split('#', 1)[0]).stat().st_mtime_ns) for path in paths}
    result = preferences.approve_sources({'paths': paths, 'signature': snapshot['signature']}, account='terminal:1000')
    assert result['status'] in {'committed', 'unchanged'}, result
    assert all(((root / path.split('#', 1)[0]).read_bytes(), (root / path.split('#', 1)[0]).stat().st_mtime_ns) == value
        for path, value in before.items())
    report.update(status='PASS', applied=True, review_status=result['status'])
    output = home / 'deployment' / ('release-' + selected['version'] + '-' + selected['commit'][:8])
    (output / 'launch-source-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
