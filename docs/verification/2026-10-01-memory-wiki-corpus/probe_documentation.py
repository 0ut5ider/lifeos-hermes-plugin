# ABOUTME: Measures managed wiki collection against pinned public LifeOS documentation.
# ABOUTME: Records native standalone controls without copying any existing installation memory.
import json
from pathlib import Path
import shutil
import re
import sys
import time

from lifeos_hook_bridge.memory_wiki import view
from test_memory_native import OWNER, SOURCE
import test_memory_wiki_render as render_fixture


output = Path(sys.argv[1])
fixture = render_fixture.MemoryWikiRenderTests()
fixture.setUp()
try:
    root = fixture.root
    for name in ('DOCUMENTATION', 'ALGORITHM'):
        shutil.copytree(SOURCE / 'LIFEOS' / name, root / 'LIFEOS' / name)
    shutil.copy2(SOURCE / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md', root / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md')
    for path in fixture.directory.glob('*.md'):
        path.unlink()
    memory = fixture.fixture.fixture.memory
    elapsed = []
    for iteration in range(3):
        start = time.monotonic()
        result = view(memory, OWNER, '/api/wiki')
        elapsed.append(time.monotonic() - start)
    native = fixture.call([fixture.request('/api/wiki')], standalone=True)[0]
    paths = [root / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
             *sorted((root / 'LIFEOS/DOCUMENTATION').rglob('*.md')),
             *sorted((root / 'LIFEOS/ALGORITHM').glob('*.md'))]
    items = [{'type': 'idea', 'title': 'Native retained source', 'content': path.read_text()} for path in paths]
    checks = memory._native('validate_batch', items=items)['results']
    write_checks = [{'path': str(path.relative_to(root)), 'ok': check.get('ok'),
                     'message': check.get('message'), 'unchanged': check.get('item') == item}
                    for path, check, item in zip(paths, checks, items, strict=True)]
    admitted = memory._native('validate_source_batch', contents=[item['content'] for item in items])['accepted']
    read_checks = [{'path': str(path.relative_to(root)), 'accepted': accepted,
                    'has_canonical_controls': bool(re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', item['content']))}
                   for path, item, accepted in zip(paths, items, admitted, strict=True)]
    summary = {'source': str(SOURCE), 'source_files': len(paths), 'source_bytes': sum(p.stat().st_size for p in paths),
        'source_max_bytes': max(p.stat().st_size for p in paths), 'managed': result['body']['stats'],
        'native': native['body']['stats'], 'seconds': elapsed, 'response_bytes': len(json.dumps(result).encode()),
        'managed_tree': result['body']['tree'], 'native_tree': native['body']['tree'],
        'write_checks': write_checks, 'read_checks': read_checks}
    output.write_text(json.dumps(summary, indent=2) + '\n')
finally:
    fixture.doCleanups()
