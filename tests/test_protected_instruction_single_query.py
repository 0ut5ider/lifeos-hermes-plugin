# ABOUTME: Verifies protected instruction writes reject an absent human approval channel.
# ABOUTME: Runs the actual pinned Hermes guard with one-shot and interactive approval contexts.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ProtectedInstructionSingleQueryTests(unittest.TestCase):
    def run_guard(self, single_query, approval):
        source = os.environ.get('LIFEOS_HERMES_SOURCE')
        if not source:
            self.skipTest('The prepared Hermes source is required')
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'config.yaml').write_text('{"approvals":{"single_query_mode":"approve"}}')
            program = '''import os
from tools.terminal_tool import set_approval_callback
from tools.file_tools_write_guards import _request_protected_instruction_approval
calls=[]
def callback(command, description, **kwargs):
 calls.append(kwargs)
 return os.environ['PAIR_APPROVAL']
set_approval_callback(callback)
result=_request_protected_instruction_approval(['CLAUDE.md'])
import json
print(json.dumps({'result':result,'calls':calls}))
'''
            env = {**os.environ, 'PYTHONPATH': str(source), 'HERMES_HOME': directory,
                   'HERMES_SINGLE_QUERY_SESSION': '1' if single_query else '', 'PAIR_APPROVAL': approval}
            result = subprocess.run([sys.executable, '-c', program], env=env, capture_output=True, text=True,
                                    timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            import json
            return json.loads(result.stdout.strip().splitlines()[-1])

    def test_single_query_never_calls_interactive_approval_even_with_approve_policy(self):
        result = self.run_guard(True, 'once')
        self.assertEqual(result['calls'], [])
        self.assertIn('no interactive user or gateway', result['result'])

    def test_interactive_one_operation_approval_remains_available(self):
        result = self.run_guard(False, 'once')
        self.assertIsNone(result['result'])
        self.assertEqual(result['calls'], [{'allow_permanent': False, 'allow_session': False}])

    def test_interactive_denial_remains_blocked(self):
        result = self.run_guard(False, 'deny')
        self.assertIn('was denied by the user', result['result'])
