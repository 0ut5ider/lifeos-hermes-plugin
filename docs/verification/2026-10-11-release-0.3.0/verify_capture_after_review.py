# ABOUTME: Checks actual native capture after an unrelated synthetic forget and explicit source review.
# ABOUTME: Preserves cursor and event bytes during refusal and resumes capture without duplicate events.
import argparse
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('package', type=Path)
args = parser.parse_args()
package = args.package.resolve()
native = '/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install'
sys.path[:0] = [str(package), str(package / 'tests'), str(package / 'hermes')]
os.environ.update(LIFEOS_MEMORY_SOURCE=native,
    LIFEOS_HARVEST_CONTROL_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install',
    PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(package) + ':' + str(package / 'tests'))
from test_memory_conduit_capture import MemoryConduitCaptureTests
from test_memory_native import OWNER
from lifeos_hook_bridge import memory_source_review as review

fixture = MemoryConduitCaptureTests()
fixture.setUp()
try:
    first = fixture.call()
    assert (first.returncode, first.stdout, first.stderr) == (0, 'captured 1 event(s)\n', '')
    memory = fixture.fixture.fixture.fixture.memory
    paths = ['LIFEOS/USER/CONDUIT/config.json', 'LIFEOS/USER/CONDUIT/state.json',
        'LIFEOS/MEMORY/STATE/work-events.jsonl', *[str(p.relative_to(fixture.root))
            for p in (fixture.data / 'events').glob('*.jsonl')]]
    before = {name: ((fixture.root / name).read_bytes(), (fixture.root / name).stat().st_mtime_ns) for name in paths}
    saved = memory.remember(OWNER, category='project', content='Synthetic unrelated retired release marker',
        title='Synthetic capture review', project='lab', request_id='release-capture-retirement')
    assert saved['status'] == 'committed', saved
    assert memory.forget(OWNER, saved['reference'], 'release-capture-forget')['status'] == 'committed'
    refused = fixture.call()
    assert refused.returncode != 0
    assert all(((fixture.root / name).read_bytes(), (fixture.root / name).stat().st_mtime_ns) == value
        for name, value in before.items())
    snapshot = review.preview(memory, OWNER, paths)
    assert all(row['accepted'] for row in snapshot['sources'])
    assert review.approve(memory, OWNER, paths, snapshot['signature'])['status'] == 'committed'
    assert all(((fixture.root / name).read_bytes(), (fixture.root / name).stat().st_mtime_ns) == value
        for name, value in before.items())
    resumed = fixture.call()
    assert (resumed.returncode, resumed.stdout, resumed.stderr) == (0, 'captured 0 event(s)\n', '')
    assert len(fixture.events()) == 1
    print(json.dumps({'status': 'PASS', 'native_capture': True, 'unreviewed_capture_refused': True,
        'review_preserves_bytes_and_timestamps': True, 'capture_resumes_without_duplicate_events': True,
        'synthetic_sources_reviewed': len(paths)}))
finally:
    fixture.doCleanups()
