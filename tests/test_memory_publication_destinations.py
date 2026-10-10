# ABOUTME: Changes actual publication destinations before receipt finalization.
# ABOUTME: Requires recoverable refusal and preserves later edits across artifact groups.
from contextlib import closing
import json
import sqlite3
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge import memory_algorithm_summary, memory_conduit_insight
from lifeos_hook_bridge import memory_local_refresh, memory_transaction
import test_memory_algorithm_summary as algorithm_fixture
import test_memory_conduit_insight as conduit_fixture
import test_memory_local_refresh_publication as local_fixture


class MemoryPublicationDestinationTests(unittest.TestCase):
    def fixture(self, kind):
        fixture = kind()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def receipts(self, memory):
        with closing(sqlite3.connect(memory.database)) as connection:
            return [json.loads(row[0]) for row in connection.execute('SELECT receipt FROM operations')]

    def assert_destination_refusal(self, memory, writer, planner, paths, destination, phase, edit, call):
        originals = {path: path.read_bytes() if path.exists() else None for path in paths}
        published, changed = {}, []
        original_publish, original_snapshot = writer.publish, planner._snapshot

        def change():
            value = json.loads(destination.read_text())
            edit(value)
            content = json.dumps(value, ensure_ascii=False, indent=2).encode()
            self.assertNotEqual(content, published[destination])
            destination.write_bytes(content)
            changed.append(content)

        def observed_publish(path, data):
            original_publish(path, data)
            if path in paths:
                published[path] = data
                if phase == 'publication' and path == destination:
                    change()

        def observed_snapshot(*args, **kwargs):
            result = original_snapshot(*args, **kwargs)
            if phase == 'snapshot' and destination in published and not changed:
                change()
            return result

        writer.publish, planner._snapshot = observed_publish, observed_snapshot
        try:
            response = call()
        finally:
            writer.publish, planner._snapshot = original_publish, original_snapshot
        self.assertEqual(len(changed), 1)
        self.assertFalse(response['ok'], response)
        self.assertTrue(memory.transaction.journal.exists())
        self.assertEqual([row['status'] for row in self.receipts(memory)], ['unknown'])
        self.assertEqual(destination.read_bytes(), changed[0])
        before_recovery = {path: path.read_bytes() for path in paths}
        with self.assertRaisesRegex(MemoryUnavailable, 'later artifact edit'):
            with memory._transaction():
                pass
        self.assertEqual({path: path.read_bytes() for path in paths}, before_recovery)
        self.assertTrue(memory.transaction.journal.exists())
        self.assertEqual([row['status'] for row in self.receipts(memory)], ['unknown'])
        destination.write_bytes(published[destination])
        with memory._transaction():
            pass
        self.assertEqual(self.receipts(memory), [])
        self.assertFalse(memory.transaction.journal.exists())
        self.assertEqual({path: path.read_bytes() if path.exists() else None for path in paths}, originals)

    def test_algorithm_cache_change_retains_recovery(self):
        for phase in ('publication', 'snapshot'):
            with self.subTest(phase=phase):
                fixture = self.fixture(algorithm_fixture.MemoryAlgorithmSummaryTests)
                prepared = fixture.prepare()
                value = fixture.value(prepared)
                def edit(current):
                    current['files']['operational-rules']['markdown'] = 'Synthetic later owner summary.'
                self.assert_destination_refusal(fixture.owner.fixture.memory,
                    memory_algorithm_summary, memory_algorithm_summary, [fixture.cache], fixture.cache, phase, edit,
                    lambda: fixture.call('algorithm_summary_publish', signature=prepared['signature'], value=value))

    def test_each_local_digest_destination_change_retains_whole_group(self):
        for phase in ('publication', 'snapshot'):
            for selected in range(3):
                with self.subTest(phase=phase, destination=selected):
                    fixture = self.fixture(local_fixture.MemoryLocalRefreshPublicationTests)
                    prepared = fixture.prepare()
                    paths = [fixture.dated(prepared), fixture.root/local_fixture.PRIMARY, fixture.root/local_fixture.FALLBACK]
                    def edit(current):
                        current['news']['items'][0]['title'] = 'Synthetic later owner local digest.'
                    self.assert_destination_refusal(fixture.owner.fixture.memory,
                        memory_transaction, memory_local_refresh, paths, paths[selected], phase, edit,
                        lambda: fixture.publish(prepared, fixture.digest()))

    def test_each_conduit_destination_change_retains_whole_group(self):
        for phase in ('publication', 'snapshot'):
            for selected in range(2):
                with self.subTest(phase=phase, destination=selected):
                    fixture = self.fixture(conduit_fixture.MemoryConduitInsightTests)
                    prepared = fixture.prepare(initialize=True)
                    paths = [fixture.insight, fixture.config]
                    value = {'date': fixture.date, 'generatedAt': fixture.date+'T12:00:00Z',
                        'conduitVersion': '1.0.0', 'level': 'low', 'model': '(none)', 'since': None,
                        'eventsConsidered': 0, 'skipped': True, 'narrative': 'No activity captured yet today.',
                        'contentTypes': []}
                    def edit(current):
                        if selected == 0:
                            current['generatedAt'] = fixture.date+'T12:01:00Z'
                        else:
                            current['pollIntervalSec'] += 120
                    self.assert_destination_refusal(fixture.fixture.fixture.memory,
                        memory_conduit_insight, memory_conduit_insight, paths, paths[selected], phase, edit,
                        lambda: MemoryService(fixture.fixture.configuration).native(fixture.fixture.context,
                            'conduit_publish', {'date': fixture.date, 'initialize': True,
                                'signature': prepared['signature'], 'value': value, 'reuse': False}))
