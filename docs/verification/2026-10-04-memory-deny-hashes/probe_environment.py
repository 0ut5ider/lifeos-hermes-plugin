# ABOUTME: Measures environment line endings at the admitted text-read boundary.
# ABOUTME: Reports only counts and equality without exposing environment values.
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_deny_hashes import MemoryDenyHashesTests
from lifeos_hook_bridge.memory_sources import _text_source
from lifeos_hook_bridge.memory_service import MemoryService

test = MemoryDenyHashesTests()
test.setUp()
try:
    before = b'SYNTHETIC_KEEP=fixture\r\nSYNTHETIC_SECOND=preserved\r\n'
    test.env.write_bytes(before)
    source, _ = _text_source(test.fixture.fixture.memory,
        MemoryService(test.fixture.configuration).scope(test.fixture.context),
        str(test.env), suffix=test.env.suffix, interview_setup=True)
    rendered = source['content'].encode()
    print(json.dumps({'physical_crlf': before.count(b'\r\n'),
        'admitted_crlf': rendered.count(b'\r\n'), 'equal': rendered == before}))
finally:
    test.doCleanups()
