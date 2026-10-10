# ABOUTME: Changes admitted sources during real native checks after publication.
# ABOUTME: Requires nested source conflicts to retain the unknown receipt and recovery journal.
from contextlib import closing
import json
import sqlite3
import unittest

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryService
import test_memory_algorithm_summary as algorithm_fixture
import test_memory_local_refresh_publication as local_fixture
import test_memory_conduit_insight as conduit_fixture


class MemoryPublicationRecheckTests(unittest.TestCase):
    def test_native_recheck_source_conflicts_retain_recovery(self):
        from lifeos_hook_bridge import memory_algorithm_summary, memory_conduit_insight, memory_transaction
        for kind in ('algorithm', 'local', 'conduit'):
            with self.subTest(kind=kind):
                if kind == 'algorithm':
                    fixture = algorithm_fixture.MemoryAlgorithmSummaryTests()
                    fixture.setUp()
                    prepared = fixture.prepare()
                    operation = 'algorithm_summary_publish'
                    arguments = {'signature':prepared['signature'], 'value':fixture.value(prepared)}
                    module, action = memory_algorithm_summary, 'algorithm_summary_plan'
                    destination, source = fixture.cache, fixture.rules
                    configuration, context, memory = fixture.configuration, fixture.owner.context, fixture.owner.fixture.memory
                    later = source.read_bytes()+b'\nSynthetic later rule during recheck.\n'
                    outputs = [destination]
                elif kind == 'local':
                    fixture = local_fixture.MemoryLocalRefreshPublicationTests()
                    fixture.setUp()
                    prepared = fixture.prepare()
                    operation = 'local_refresh_publish'
                    arguments = {'signature':prepared['signature'], 'value':fixture.digest()}
                    module, action = memory_transaction, 'local_refresh_inputs'
                    destination, source = fixture.dated(prepared), fixture.identity
                    configuration, context, memory = fixture.configuration, fixture.owner.context, fixture.owner.fixture.memory
                    later = source.read_bytes()+b'\nSynthetic later identity during recheck.\n'
                    outputs = [destination, fixture.root/local_fixture.PRIMARY, fixture.root/local_fixture.FALLBACK]
                else:
                    fixture = conduit_fixture.MemoryConduitInsightTests()
                    fixture.setUp()
                    prepared = fixture.prepare(initialize=True)
                    operation = 'conduit_publish'
                    arguments = {'date':fixture.date, 'initialize':True, 'signature':prepared['signature'], 'reuse':False,
                        'value':{'date':fixture.date, 'generatedAt':'2026-10-09T12:00:00Z', 'conduitVersion':'1.0.0',
                            'level':'low', 'model':'(none)', 'since':None, 'eventsConsidered':0, 'skipped':True,
                            'narrative':'No activity captured yet today.', 'contentTypes':[]}}
                    module, action = memory_conduit_insight, 'conduit_prepare'
                    destination, source = fixture.insight, fixture.events
                    configuration, context, memory = fixture.fixture.configuration, fixture.fixture.context, fixture.fixture.fixture.memory
                    later = (json.dumps({'ts':fixture.date+'T12:00:00Z', 'type':'app-focus', 'source':'synthetic',
                        'app':'Synthetic later application during recheck'})+'\n').encode()
                    outputs = [destination, fixture.config]
                self.addCleanup(fixture.doCleanups)
                original_publish, original_native = module.publish, NativeMemory._native
                published, changed = [], []
                def observed_publish(path, data):
                    original_publish(path, data)
                    if path == destination: published.append(path)
                def observed_native(owner, selected, **values):
                    result = original_native(owner, selected, **values)
                    if published and selected == action and not changed:
                        source.parent.mkdir(parents=True, exist_ok=True)
                        source.write_bytes(later)
                        changed.append(selected)
                    return result
                module.publish, NativeMemory._native = observed_publish, observed_native
                try:
                    response = MemoryService(configuration).native(context, operation, arguments)
                finally:
                    module.publish, NativeMemory._native = original_publish, original_native
                self.assertFalse(response['ok'], response)
                self.assertEqual(changed, [action])
                self.assertTrue(memory.transaction.journal.exists())
                with closing(sqlite3.connect(memory.database)) as connection:
                    receipts = [json.loads(row[0]) for row in connection.execute('SELECT receipt FROM operations')]
                self.assertEqual([row['status'] for row in receipts], ['unknown'])
                with memory._transaction(): pass
                for path in outputs: self.assertFalse(path.exists(), path)
                self.assertEqual(source.read_bytes(), later)
