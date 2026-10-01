# ABOUTME: Measures source traversal and private metadata handling in disposable fixtures.
# ABOUTME: Preserves actual filesystem behavior while counting directory iterator yields.
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_wiki import _files, view
from test_memory_native import OWNER
from test_memory_wiki_corpus import MemoryWikiCorpusTests

@contextmanager
def counted_entries():
    original = Path.iterdir
    counts = {'yielded': 0}
    def observed(path):
        for child in original(path):
            counts['yielded'] += 1
            yield child
    with patch.object(Path, 'iterdir', observed):
        yield counts

results = {}
with tempfile.TemporaryDirectory(prefix='memory-review-traversal-') as temporary:
    root = Path(temporary)
    for i in range(6000):
        (root / f'entry-{i:05}.txt').touch()
    with counted_entries() as counts:
        try:
            _files(root)
        except MemoryUnavailable as error:
            results['non_markdown_wide_directory'] = dict(counts, error=str(error), entries=6000)
with tempfile.TemporaryDirectory(prefix='memory-review-hidden-') as temporary:
    root = Path(temporary)
    for i in range(3000):
        (root / f'.hidden-{i:05}').touch()
    with counted_entries() as counts:
        selected = _files(root)
        results['hidden_entries'] = dict(counts, selected=len(selected), entries=3000)
fixture = MemoryWikiCorpusTests()
fixture.setUp()
try:
    for relative in ('DOCUMENTATION', 'MEMORY/WISDOM/FRAMES', 'MEMORY/RESEARCH'):
        directory = fixture.root / 'LIFEOS' / relative
        directory.mkdir(parents=True)
        for i in range(1100):
            (directory / f'unrelated-{i:05}.txt').touch()
    with counted_entries() as counts:
        response = view(fixture.memory, OWNER, '/api/wiki')
        results['combined_source_roots'] = dict(counts, status=response['status'], entries=3300)
finally:
    fixture.doCleanups()
fixture = MemoryWikiCorpusTests()
fixture.setUp()
try:
    work = fixture.root / 'LIFEOS/MEMORY/WORK'
    work.mkdir()
    for i in range(3000):
        (work / f'unrelated-{i:05}').touch()
    with counted_entries() as counts:
        response = view(fixture.memory, OWNER, '/api/wiki')
        results['work_entries'] = dict(counts, status=response['status'], entries=3000)
    path = fixture.source('DOCUMENTATION/<private>SyntheticPrivateFilename.md', 'Safe body without title\n')
    response = view(fixture.memory, OWNER, '/api/wiki')
    results['private_filename'] = {'status': response['status'], 'private_marker_returned': 'SyntheticPrivateFilename' in json.dumps(response), 'response': response}
finally:
    fixture.doCleanups()
print(json.dumps(results, indent=2))
