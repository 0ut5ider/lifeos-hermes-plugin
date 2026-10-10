# ABOUTME: Compares native latest-digest retention for complete JSON cache forms.
# ABOUTME: Requires empty refreshes to preserve populated array caches and their source bytes.
import json
import unittest
import test_memory_local_refresh_publication as fixture
from lifeos_hook_bridge.memory_local_intelligence import PRIMARY, FALLBACK


class MemoryLocalRefreshCacheTests(unittest.TestCase):
    setUp = fixture.MemoryLocalRefreshPublicationTests.setUp
    call = fixture.MemoryLocalRefreshPublicationTests.call
    digest = fixture.MemoryLocalRefreshPublicationTests.digest
    prepare = fixture.MemoryLocalRefreshPublicationTests.prepare
    publish = fixture.MemoryLocalRefreshPublicationTests.publish
    dated = fixture.MemoryLocalRefreshPublicationTests.dated

    def test_populated_array_latest_retains_native_no_clobber_behavior(self):
        value = [self.digest()['news']]
        for relative in (PRIMARY, FALLBACK):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        before = [(self.root / relative).read_bytes() for relative in (PRIMARY, FALLBACK)]
        prepared = self.prepare()
        result = self.publish(prepared, self.digest(populated=False))
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['summary']['latestSkipped'])
        self.assertEqual([(self.root / relative).read_bytes() for relative in (PRIMARY, FALLBACK)], before)
