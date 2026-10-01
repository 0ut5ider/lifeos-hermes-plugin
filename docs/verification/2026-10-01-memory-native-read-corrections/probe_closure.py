# ABOUTME: Measures real directory iteration and source metadata admission in synthetic fixtures.
# ABOUTME: Saves isolated closure evidence without changing product files or prepared sources.
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import json
import os
import tempfile

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_wiki import _files, view
from lifeos_hook_bridge.memory_sources import read_markdown
from test_memory_wiki_corpus import MemoryWikiCorpusTests
from test_memory_native import OWNER

OUTPUT = Path(__file__).resolve().parent / 'raw'
RESULTS = []

@contextmanager
def observed_scan():
    original = os.scandir
    observations = []
    @contextmanager
    def observe(path):
        with original(path) as entries:
            def counted():
                for entry in entries:
                    observations.append(str(path))
                    yield entry
            yield counted()
    with patch.object(os, 'scandir', observe):
        yield observations

def direct_scan(label, population, hidden=False):
    with tempfile.TemporaryDirectory(prefix='closure-scan-') as temporary:
        directory = Path(temporary)
        for index in range(population):
            (directory / (('.' if hidden else '') + f'entry-{index}.txt')).touch()
        error = None
        with observed_scan() as observations:
            try:
                selected = _files(directory)
            except MemoryUnavailable as caught:
                selected = None
                error = str(caught)
        expected = min(population, 2049)
        assert len(observations) == expected, (label, len(observations))
        assert bool(error) == (population > 2048), (label, error)
        RESULTS.append(dict(case=label, population=population, consumed=len(observations),
                            selected=selected, error=error))

def retained_scan(label, populations):
    fixture = MemoryWikiCorpusTests()
    fixture.setUp()
    try:
        for relative, population in populations:
            directory = fixture.root / 'LIFEOS' / relative
            directory.mkdir(parents=True, exist_ok=True)
            for index in range(population):
                (directory / f'entry-{index}.txt').touch()
        with observed_scan() as observations:
            try:
                view(fixture.memory, OWNER, '/api/wiki')
            except MemoryUnavailable as caught:
                error = str(caught)
            else:
                raise AssertionError('Expected retained scan refusal')
        assert len(observations) == 2049, (label, len(observations))
        assert 'traversal count limit' in error
        counts = {path: observations.count(path) for path in sorted(set(observations))}
        RESULTS.append(dict(case=label, populations=populations, consumed=len(observations),
                            by_directory=counts, error=error))
    finally:
        fixture.doCleanups()

def metadata():
    fixture = MemoryWikiCorpusTests()
    fixture.setUp()
    try:
        denied = ('DOCUMENTATION/<private>ClosureFilename.md',
                  'DOCUMENTATION/<pr\u200bivate>ClosureGroup/public.md',
                  'MEMORY/WORK/<\uff50\uff52\uff49\uff56\uff41\uff54\uff45>ClosureWork/ISA.md',
                  'MEMORY/WISDOM/FRAMES/Closure\u0085Control.md',
                  'MEMORY/RESEARCH/Closure\x7fDelete.md',
                  'ALGORITHM/<private ClosureMalformed.md')
        paths = [fixture.source(relative, 'Safe content [[closure-target]]\n') for relative in denied]
        fixed = fixture.source('LIFEOS_SYSTEM_PROMPT.md', '<private>ClosureFixedBody</private>\n')
        public = fixture.source('DOCUMENTATION/Public Group/closure-public.md',
                                'Safe ordinary content [[closure-target]] [[unpublished-target]]\n')
        fixture.source('MEMORY/RESEARCH/closure-target.md', '# Closure public target\nTarget content\n')
        targets = ['/api/wiki', '/api/wiki/graph', '/api/wiki/search?q=Safe',
                   '/api/wiki/doc/Public%20Group__closure-public',
                   '/api/wiki/backlinks/closure-target', '/api/wiki/backlinks/unpublished-target',
                   '/api/wiki/backlinks/absent-target']
        results = [view(fixture.memory, OWNER, target) for target in targets]
        serialized = json.dumps(results)
        for marker in ('ClosureFilename', 'ClosureGroup', 'ClosureWork', 'Control', 'Delete',
                       'ClosureMalformed', 'ClosureFixedBody'):
            assert marker not in serialized, marker
        assert results[3]['body']['title'] == public.stem
        assert results[3]['body']['group'] == 'Public Group'
        for index in (4, 5):
            assert len(results[index]['body']['backlinks']) == 1
            assert results[index]['body']['backlinks'][0]['slug'] == 'Public Group__closure-public'
        assert results[6]['body']['backlinks'] == []
        assert all(path.read_text() == 'Safe content [[closure-target]]\n' for path in paths)
        assert 'ClosureFixedBody' in fixed.read_text()
        RESULTS.append(dict(case='metadata-native-routes', denied_sources=list(denied),
                            targets=targets, responses=results, raw_sources_unchanged=True))
    finally:
        fixture.doCleanups()

def path_guards():
    for kind in ('work-isa-link', 'nested-documentation-link', 'parent-traversal'):
        fixture = MemoryWikiCorpusTests()
        fixture.setUp()
        try:
            target = fixture.source('DOCUMENTATION/real.md', '# Closure allowed target\n')
            if kind == 'work-isa-link':
                link = fixture.root / 'LIFEOS/MEMORY/WORK/synthetic/ISA.md'
                link.parent.mkdir(parents=True)
                link.symlink_to(target)
            elif kind == 'nested-documentation-link':
                link = fixture.root / 'LIFEOS/DOCUMENTATION/alias'
                link.symlink_to(target.parent)
            try:
                if kind == 'parent-traversal':
                    path = str(target.parent) + '/../DOCUMENTATION/real.md'
                    read_markdown(fixture.memory, OWNER, [path])
                else:
                    view(fixture.memory, OWNER, '/api/wiki')
            except MemoryUnavailable as caught:
                RESULTS.append(dict(case=kind, error=str(caught)))
            else:
                raise AssertionError('Expected exact-path refusal: ' + kind)
        finally:
            fixture.doCleanups()

for arguments in [('visible-overflow', 6000, False), ('hidden-overflow', 3000, True),
                  ('exact-boundary', 2048, True), ('next-entry-refusal', 2049, True)]:
    direct_scan(*arguments)
retained_scan('work-nonsources', [('MEMORY/WORK', 3000)])
retained_scan('shared-roots', [('DOCUMENTATION', 1100), ('ALGORITHM', 1100), ('MEMORY/WORK', 1100)])
metadata()
path_guards()
(OUTPUT / 'closure-probes.json').write_text(json.dumps(RESULTS, indent=2) + '\n')
print(json.dumps({'cases_passed': len(RESULTS), 'output': str(OUTPUT / 'closure-probes.json')}))
