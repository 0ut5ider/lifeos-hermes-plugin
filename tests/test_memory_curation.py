# ABOUTME: Verifies native reviewers and direct writers share governed publication and revisions.
# ABOUTME: Uses real native curation, malformed input, and stale snapshots in synthetic stores.

from dataclasses import replace
import unittest

from lifeos_hook_bridge.memory_access import HOT_FILES
import test_memory_native as native_fixture


class MemoryCurationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.scope = native_fixture.OWNER

    def test_native_add_and_full_curation_preserve_current_references(self):
        saved = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal", "content": "RULE: original native fact"},
                                        request_id="native-first", project="general")
        self.assertTrue(saved["ok"], saved)
        first = self.memory.recall(self.scope, "original native fact")[0]
        observed = self.memory.read_hot(self.scope, "principal")
        curated = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal", "op": "set",
                                                      "entries": ["RULE: original native fact", "RULE: added native fact"]},
                                         request_id="native-set", project="general", observed_revision=observed["revision"])
        self.assertTrue(curated["ok"], curated)
        self.assertEqual(self.memory.get(self.scope, first["reference"])["status"], "ok")
        self.assertEqual(len(self.memory.recall(self.scope, "native fact")), 2)

    def test_hot_mutations_refuse_neighbor_drift_without_retiring_records(self):
        for category in ('principal', 'assistant'):
            for drift in ('overlength', 'valid_addition', 'valid_change'):
                fixture = native_fixture.NativeMemoryTests()
                fixture.setUp()
                try:
                    first = fixture.remember('RULE: Synthetic target fact', 'first', category)
                    fixture.remember('RULE: Synthetic neighboring fact', 'second', category)
                    path = fixture.root / HOT_FILES[category]
                    text = path.read_text()
                    if drift == 'overlength':
                        text = text.replace('RULE: Synthetic neighboring fact', 'RULE: ' + 'x' * 300)
                    elif drift == 'valid_change':
                        text = text.replace('RULE: Synthetic neighboring fact', 'RULE: Synthetic changed neighbor')
                    else:
                        text = text.replace('<!-- END ENTRIES -->',
                            'RULE: Synthetic unmanaged neighbor\n<!-- END ENTRIES -->')
                    path.write_text(text)
                    before = path.read_bytes()
                    with fixture.memory._transaction() as connection:
                        records = [dict(row) for row in connection.execute('SELECT * FROM records ORDER BY id')]
                    for operation in ('correct', 'forget'):
                        with self.subTest(category=category, drift=drift, operation=operation):
                            arguments = [self.scope, first['reference']]
                            if operation == 'correct':
                                arguments.append('RULE: Synthetic replacement fact')
                            arguments.append('drift-' + operation)
                            receipt = getattr(fixture.memory, operation)(*arguments)
                            self.assertIn(receipt['status'], ('conflict', 'rejected'), receipt)
                            self.assertEqual(path.read_bytes(), before)
                            with fixture.memory._transaction() as connection:
                                actual = [dict(row) for row in connection.execute('SELECT * FROM records ORDER BY id')]
                            self.assertEqual(actual, records)
                finally:
                    fixture.doCleanups()

    def test_stale_native_reviewer_cannot_overwrite_an_acknowledged_fact(self):
        self.fixture.remember("RULE: original native fact", "first", "principal")
        observed = self.memory.read_hot(self.scope, "principal")
        self.fixture.remember("RULE: acknowledged explicit fact", "second", "principal")
        result = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal", "op": "set",
                                                    "entries": ["RULE: reviewer replacement"]}, request_id="stale", project="general",
                                       observed_revision=observed["revision"])
        self.assertFalse(result["ok"])
        self.assertIn("revision", result["message"])
        self.assertEqual(len(self.memory.recall(self.scope, "fact")), 2)

    def test_forgotten_fact_cannot_return_with_changed_prefix_or_provenance(self):
        saved = self.fixture.remember("RULE: original retained fact", "first", "principal")
        self.memory.forget(self.scope, saved["reference"], "forget")
        result = self.memory.native_add(self.scope, {"type": "memory", "actor": "principal",
                                                    "content": "PREFERENCE: Original retained fact ~inferred"}, request_id="resurrection", project="general")
        self.assertFalse(result["ok"])
        self.assertEqual(self.memory.recall(self.scope, "retained"), [])

    def test_direct_native_set_cannot_silently_drop_invalid_replacements(self):
        self.fixture.remember("RULE: original native fact", "first", "principal")
        observed = self.memory.read_hot(self.scope, "principal")
        result = self.memory.native_set(self.scope, "principal", ["RULE: " + "😀" * 129], "invalid", observed["revision"])
        self.assertFalse(result["ok"])
        self.assertEqual(len(self.memory.recall(self.scope, "original")), 1)

    def test_explicit_remember_refuses_unadopted_hot_entries_without_changing_bytes(self):
        for category in ('principal', 'assistant'):
            with self.subTest(category=category):
                result = self.memory._native('add', item={'type': 'memory', 'actor': category,
                    'content': 'RULE: Synthetic unadopted control'})
                self.assertTrue(result['ok'], result)
                path = self.fixture.root / HOT_FILES[category]
                before = path.read_bytes()
                saved = self.fixture.remember('RULE: Synthetic governed addition', 'unadopted-' + category, category)
                self.assertEqual(saved['status'], 'conflict', saved)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(self.memory.recall(self.scope, 'governed addition'), [])

    def test_explicit_remember_refuses_out_of_band_addition_and_changed_record(self):
        self.fixture.remember('RULE: Synthetic adopted control', 'original', 'principal')
        path = self.fixture.root / HOT_FILES['principal']
        self.memory._native('add', item={'type': 'memory', 'actor': 'principal',
            'content': 'RULE: Synthetic outside addition'})
        for content in ('RULE: Synthetic acknowledged addition', 'RULE: Synthetic adopted control'):
            with self.subTest(content=content):
                before = path.read_bytes()
                result = self.fixture.remember(content, 'outside-' + content, 'principal')
                self.assertEqual(result['status'], 'conflict', result)
                self.assertEqual(path.read_bytes(), before)
        path.write_text(path.read_text().replace('Synthetic adopted control', 'Synthetic changed control'))
        before = path.read_bytes()
        result = self.fixture.remember('RULE: Synthetic changed-store addition', 'changed-store', 'principal')
        self.assertEqual(result['status'], 'conflict', result)
        self.assertEqual(path.read_bytes(), before)

    def test_explicit_remember_after_adoption_preserves_native_refs_and_provenance(self):
        self.memory._native('add', item={'type': 'memory', 'actor': 'principal',
            'content': 'RULE: Synthetic adopted control'})
        preview = self.memory.preview_adoption(self.scope)
        adopted = self.memory.adopt(self.scope, preview['signature'], {}, 'adopt-hot')
        self.assertEqual(adopted['status'], 'committed', adopted)
        prior = self.memory.recall(self.scope, 'adopted control')[0]['reference']
        source = {'kind': 'explicit', 'session': 'synthetic-owner-session'}
        arguments = dict(category='principal', content='RULE: Synthetic explicit addition', title='', project='', source=source)
        result = self.memory.remember(self.scope, request_id='after-adoption', **arguments)
        self.assertEqual(result['status'], 'committed', result)
        self.assertEqual(self.memory.remember(self.scope, request_id='after-adoption', **arguments), result)
        self.assertEqual(self.memory.get(self.scope, prior)['status'], 'ok')
        saved = self.memory.get(self.scope, result['reference'])
        self.assertEqual(saved['source']['session'], source['session'])
        self.assertEqual(saved['source']['kind'], 'explicit')
        self.assertEqual(self.memory.read_hot(self.scope, 'principal')['entries'],
            ['RULE: Synthetic adopted control', 'RULE: Synthetic explicit addition'])

    def test_explicit_hot_remember_requires_read_and_write_grants(self):
        scope = replace(self.scope, read=())
        path = self.fixture.root / HOT_FILES['principal']
        before = path.read_bytes()
        result = self.memory.remember(scope, category='principal', content='RULE: Synthetic blind append',
            title='', project='', request_id='blind-append')
        self.assertEqual(result['status'], 'rejected', result)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
