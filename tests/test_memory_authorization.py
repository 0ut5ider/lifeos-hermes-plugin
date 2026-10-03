# ABOUTME: Audits real source access during permitted and denied memory mutations.
# ABOUTME: Uses synthetic native files to verify authorization before recovery copies.
import sys
import unittest
from dataclasses import replace

from lifeos_hook_bridge.memory_policy import MemoryScope
import test_memory_native as native


class MemoryAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.events = []
        self.tracked = set()
        self.auditing = False
        def audit(event, arguments):
            if self.auditing and event == 'open' and arguments[0] in self.tracked:
                self.events.append(arguments)
        sys.addaudithook(audit)

    def observe(self, reference, action):
        with self.memory._transaction() as connection:
            row = connection.execute('SELECT path FROM records WHERE id=?', (reference['id'],)).fetchone()
        path = self.fixture.root / row['path']
        self.tracked = {str(path), str(path.resolve())}
        before = path.read_bytes()
        self.events.clear()
        self.auditing = True
        try:
            result = action()
        finally:
            self.auditing = False
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.events, [], 'A denied or stale request opens the native source')
        return result

    def test_denied_correct_and_forget_do_not_read_category_or_project_sources(self):
        restricted = MemoryScope('client', 'mcp:writer', ('project',), ('project',), ('other',), 'restricted')
        for category in ('principal', 'assistant', 'project'):
            saved = self.fixture.remember('RULE: Synthetic private source ' + category, 'private-' + category, category)
            for operation in ('correct', 'forget'):
                with self.subTest(category=category, operation=operation):
                    arguments = [restricted, saved['reference']]
                    if operation == 'correct':
                        arguments.append('RULE: Synthetic unauthorized replacement')
                    arguments.append('denied-' + operation + '-' + category)
                    result = self.observe(saved['reference'], lambda: getattr(self.memory, operation)(*arguments))
                    self.assertEqual(result['status'], 'rejected', result)

    def test_stale_correct_and_forget_do_not_read_sources_before_refusal(self):
        saved = self.fixture.remember('RULE: Synthetic obsolete source', 'obsolete', 'principal')
        corrected = self.memory.correct(native.OWNER, saved['reference'], 'RULE: Synthetic current source', 'correction')
        self.assertEqual(corrected['status'], 'committed', corrected)
        for operation in ('correct', 'forget'):
            with self.subTest(operation=operation):
                arguments = [native.OWNER, saved['reference']]
                if operation == 'correct':
                    arguments.append('RULE: Synthetic stale replacement')
                arguments.append('stale-' + operation)
                result = self.observe(saved['reference'], lambda: getattr(self.memory, operation)(*arguments))
                self.assertEqual(result['status'], 'conflict', result)

    def test_hot_correct_and_forget_require_read_before_opening_the_whole_file(self):
        blind = replace(native.OWNER, read=(), writer='synthetic:blind-writer')
        for category in ('principal', 'assistant'):
            saved = self.fixture.remember('RULE: Synthetic unreadable ' + category, category, category)
            for operation in ('correct', 'forget'):
                with self.subTest(category=category, operation=operation):
                    arguments = [blind, saved['reference']]
                    if operation == 'correct':
                        arguments.append('RULE: Synthetic blind replacement')
                    arguments.append('blind-' + operation + '-' + category)
                    result = self.observe(saved['reference'], lambda: getattr(self.memory, operation)(*arguments))
                    self.assertEqual(result['status'], 'rejected', result)
