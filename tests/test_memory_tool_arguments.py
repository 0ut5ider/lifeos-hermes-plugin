# ABOUTME: Checks the bounds that memory tool arguments must meet before any native worker runs.
# ABOUTME: Covers nested proposal fields, which a client with proposal permission controls.
import unittest

from lifeos_hook_bridge.memory_service import _validate_arguments


def proposal(**changes):
    value = {'type': 'proposal', 'target_kind': 'rule', 'target_file': '/synthetic/RULES.md',
             'edit': 'Synthetic edit.', 'confidence': 0.5, 'rationale': 'Synthetic rationale.',
             'source_session': 'session-1', 'observed_across_sessions': 2}
    value.update(changes)
    return {'proposal': value, 'request_id': 'request-1'}


class MemoryToolArgumentTests(unittest.TestCase):
    def test_a_bounded_proposal_is_accepted(self):
        _validate_arguments('lifeos_memory_propose', proposal())

    def test_oversized_or_mistyped_proposal_fields_are_refused(self):
        cases = {
            'edit': 'x' * 65537, 'rationale': 'x' * 8193, 'target_file': 'x' * 4097,
            'target_kind': 'x' * 65, 'source_session': 'x' * 257,
            'confidence': 'high', 'observed_across_sessions': 10 ** 7,
        }
        for field, value in cases.items():
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'proposal'):
                _validate_arguments('lifeos_memory_propose', proposal(**{field: value}))
        for field, value in (('confidence', True), ('observed_across_sessions', 1.5), ('edit', '')):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'proposal'):
                _validate_arguments('lifeos_memory_propose', proposal(**{field: value}))


if __name__ == '__main__':
    unittest.main()
