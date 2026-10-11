# ABOUTME: Checks capacity fallback and accounting with real native temporary user fixtures.
# ABOUTME: Preserves review measurements without changing implementation or repository tests.
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from test_memory_atlas_retention import MemoryAtlasRetentionTests

out = Path(__file__).parent
measurements = {}

class AdditionalCases(unittest.TestCase):
    def fixture(self):
        fixture = MemoryAtlasRetentionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_protected_only_capacity_fallback(self):
        f = self.fixture()
        f.inventory(0,84)
        initial = f.sync()
        self.assertTrue(initial['ok'], initial)
        f.seed_runs(2)
        before = f.graph().read_bytes()
        with closing(sqlite3.connect(f.graph())) as c:
            references = {r[0] for r in c.execute('SELECT last_run_id FROM source_observation UNION SELECT last_run_id FROM edge_observation')}
        result = f.sync()
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['history']['capacity_compacted'], result)
        self.assertEqual((result['history']['run_retain'],result['history']['event_retain']),(0,0))
        archive = f.archive(result)
        self.assertEqual((archive/'atlas.db').read_bytes(),before)
        with closing(sqlite3.connect(f.graph())) as c:
            identifiers = {r[0] for r in c.execute('SELECT id FROM sync_run')}
            assets = c.execute('SELECT COUNT(*) FROM asset').fetchone()[0]
        self.assertTrue(references <= identifiers)
        self.assertEqual(assets,252)
        measurements['protected_only'] = {'initial':initial,'result':result,'prior_references':sorted(references),'after_run_identifiers':sorted(identifiers),'before_sha256':hashlib.sha256(before).hexdigest()}

    def test_mixed_success_and_partial_accounting_and_distinct_timestamp(self):
        f = self.fixture()
        f.prepare_history()
        with closing(sqlite3.connect(f.graph())) as c:
            c.execute("UPDATE sync_run SET status='success',complete=1 WHERE id%3=0")
            c.execute("UPDATE sync_run SET finished_at='2099-01-01T00:00:00Z' WHERE id=3")
            c.commit()
            before = {r[0]: {'runs':r[1],'successes':r[2]} for r in c.execute("SELECT collector,COUNT(*),SUM(status='success') FROM sync_run GROUP BY collector")}
            assets = c.execute('SELECT id,canonical_key FROM asset ORDER BY id').fetchall()
        first = f.sync()
        self.assertTrue(first['ok'],first)
        snapshot = json.loads(f.graph().with_name('snapshot.json').read_text())
        totals = {r['collector']:{'runs':r['runs'],'successes':r['successes']} for r in snapshot['status']['collectors']}
        expected = {name:{key:value+1 for key,value in count.items()} for name,count in before.items()}
        self.assertEqual(totals,expected)
        self.assertEqual(next(r['last_run'] for r in snapshot['status']['collectors'] if r['collector']=='gear'),'2099-01-01T00:00:00Z')
        with closing(sqlite3.connect(f.graph())) as c:
            self.assertIsNotNone(c.execute('SELECT id FROM sync_run WHERE id=3').fetchone())
            self.assertEqual(c.execute('SELECT id,canonical_key FROM asset ORDER BY id').fetchall(),assets)
        f.seed_runs(64)
        second = f.sync()
        self.assertTrue(second['ok'],second)
        snapshot2 = json.loads(f.graph().with_name('snapshot.json').read_text())
        totals2 = {r['collector']:{'runs':r['runs'],'successes':r['successes']} for r in snapshot2['status']['collectors']}
        expected['gear']['runs'] += 65
        expected['gear']['successes'] += 1
        expected['projects']['runs'] += 1
        expected['projects']['successes'] += 1
        self.assertEqual(totals2,expected)
        measurements['mixed_accounting'] = {'before':before,'first':first,'first_totals':totals,'second':second,'second_totals':totals2}

if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        (out/'additional-measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
