# ABOUTME: Changes actual Discord permissions after native memory read and preview processing.
# ABOUTME: Verifies governed source responses cannot escape through retained caller authority.
from unittest.mock import patch
import unittest

from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_native import OWNER
import test_memory_background_audience as audience_fixture


class MemoryNativeResponseAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture=audience_fixture.MemoryBackgroundAudienceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        result=self.fixture.fixture.memory.remember(OWNER,category='project',content='Synthetic response authority private fact',
            title='Synthetic response authority fact',project='lab',request_id='response-authority-fact')
        self.assertEqual(result['status'],'committed',result)
        staged=self.fixture.root/'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue/Research/synthetic-response-preview.md'
        staged.parent.mkdir(parents=True)
        staged.write_text('---\ntitle: "Synthetic private preview title"\ntype: research\ndomain: research\n'
            'created: 2026-10-08\nquality: 5\nstatus: pending-review\nharvested_from: synthetic-source\n---\n\n'
            '# Synthetic private preview title\n\nSynthetic reviewed staging body\n')

    def exercise(self,operation,arguments,action):
        real_native=NativeMemory._native
        def observe(memory,name,**values):
            result=real_native(memory,name,**values)
            if name==action:self.fixture.open_channel()
            return result
        with patch.object(NativeMemory,'_native',observe):
            result=self.fixture.service.native(self.fixture.context,operation,arguments)
        self.assertTrue(self.fixture.changed,'The test must reach actual native processing')
        self.assertFalse(result.get('ok'),result)
        self.assertNotIn('records',result)
        self.assertNotIn('notes',result)
        self.assertIn('/channels/60',self.fixture.audience.requests)

    def test_canonical_corpus_rechecks_authority_after_native_parsing(self):
        self.exercise('canonical_corpus',{'root':str(self.fixture.root/'LIFEOS/MEMORY')},'canonical_records')

    def test_staged_preview_rechecks_authority_after_index_rendering(self):
        self.exercise('staged_preview',{'target':'Research/synthetic-response-preview','all':False,'project':'lab'},
                      'knowledge_indexes')


    def test_authority_changed_after_commit_withholds_the_response_and_preserves_the_receipt(self):
        actual_add=NativeMemory.native_add
        def observe(memory,scope,*arguments,**options):
            result=actual_add(memory,scope,*arguments,**options)
            self.fixture.open_channel()
            return result
        arguments={'item':{'type':'memory','actor':'principal','content':'RULE: Synthetic postpublication authority fact'},
                   'request_id':'postpublication-authority','project':'','observed_revision':None}
        with patch.object(NativeMemory,'native_add',observe):
            result=self.fixture.service.native(self.fixture.context,'add',arguments)
        self.assertTrue(self.fixture.changed)
        self.assertFalse(result['ok'],result)
        self.assertEqual(result['code'],'EACCESS_CHANGED')
        self.assertIn('response is withheld',result['message'])
        self.assertNotIn('receipt',result)
        facts=[row for row in self.fixture.fixture.memory.recall(OWNER,'Synthetic postpublication authority fact')
               if row['content']=='RULE: Synthetic postpublication authority fact']
        self.assertEqual(len(facts),1)
        self.fixture.audience.responses['/channels/60']['permission_overwrites'].pop()
        retry=self.fixture.service.native(self.fixture.context,'add',arguments)
        self.assertTrue(retry['ok'],retry)
        self.assertEqual(len([row for row in self.fixture.fixture.memory.recall(OWNER,'Synthetic postpublication authority fact')
                              if row['content']=='RULE: Synthetic postpublication authority fact']),1)

    def test_unchanged_owner_receives_the_native_canonical_response(self):
        result=self.fixture.service.native(self.fixture.context,'canonical_corpus',
            {'root':str(self.fixture.root/'LIFEOS/MEMORY')})
        self.assertTrue(result['ok'],result)
        self.assertIn('Synthetic response authority private fact',result['records'][0]['content'])


if __name__=='__main__':
    unittest.main()
