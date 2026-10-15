# ABOUTME: Prevents model narration from satisfying native memory acceptance without a real tool result.
# ABOUTME: Checks rejected, malformed, repeated, and incomplete search results with synthetic protocol events.
import copy
import json
import unittest

from .model_turn_assertions import verified_search


class ModelTurnAssertions(unittest.TestCase):
    def setUp(self):
        self.expected='SYNTHETIC-MARKER'
        self.reference={'id':'1'*32,'revision':1}
        self.events=[{'type':'tool_use','name':'lifeos_memory_search'},
            {'type':'tool_result','name':'lifeos_memory_search','is_error':False,
                'output':json.dumps({'status':'ok','results':[{'reference':self.reference,
                    'content':'Synthetic fact '+self.expected,'status':'active'}]})}]

    def test_real_success_exports_only_matching_reference(self):
        self.assertEqual(verified_search(self.events,self.expected),{'verified':True,'references':[self.reference]})

    def test_claimed_final_answer_does_not_replace_rejected_tool_result(self):
        self.events[-1]['output']=json.dumps({'status':'rejected','reason':'No grant'})
        self.events.append({'type':'result','text':self.expected})
        self.assertFalse(verified_search(self.events,self.expected)['verified'])

    def test_malformed_output_and_protocol_error_are_refused(self):
        for output,error in [('not JSON',False),(self.events[-1]['output'],True)]:
            events=copy.deepcopy(self.events);events[-1].update(output=output,is_error=error)
            self.assertFalse(verified_search(events,self.expected)['verified'])

    def test_missing_or_invalid_reference_does_not_verify_fact(self):
        for reference in [None,{}, {'id':'1'*32,'revision':True}]:
            events=copy.deepcopy(self.events)
            events[-1]['output']=json.dumps({'status':'ok','results':[{'content':self.expected,'reference':reference}]})
            self.assertFalse(verified_search(events,self.expected)['verified'])

    def test_repeated_tool_calls_and_unmatched_fact_are_refused(self):
        events=self.events+[self.events[0]]
        self.assertFalse(verified_search(events,self.expected)['verified'])
        self.assertFalse(verified_search(self.events,'ANOTHER-MARKER')['verified'])
