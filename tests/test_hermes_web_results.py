# ABOUTME: Verifies Hermes classifies actual web extraction envelopes before text heuristics.
# ABOUTME: Prevents successful external content from bypassing LifeOS PostToolUse safety hooks.

import json
import unittest


class HermesWebResultsTests(unittest.TestCase):
    def classify(self, results):
        from agent.display import _detect_tool_failure
        from agent.tool_guardrails import classify_tool_failure
        body = json.dumps({'results': results})
        detected = _detect_tool_failure('web_extract', body)[0]
        self.assertEqual(detected, classify_tool_failure('web_extract', body)[0])
        return detected

    def test_null_error_on_successful_extraction_is_success(self):
        self.assertFalse(self.classify([{'url': 'https://fixture.invalid', 'content': 'Fixture text', 'error': None}]))

    def test_document_text_cannot_set_the_execution_status(self):
        self.assertFalse(self.classify([{'content': 'The JSON example has "error" and "failed" keys.', 'error': None}]))

    def test_partial_success_preserves_successful_external_content(self):
        self.assertFalse(self.classify([{'content': 'Fixture text', 'error': None}, {'error': 'Document unavailable'}]))

    def test_complete_failure_remains_a_failure(self):
        self.assertTrue(self.classify([{'content': '', 'error': 'Document unavailable'}]))

    def test_top_level_failure_remains_a_failure(self):
        from agent.display import _detect_tool_failure
        self.assertTrue(_detect_tool_failure('web_extract', '{"error":"Extraction failed"}')[0])
