# ABOUTME: Exercises the actual Algorithm edit transport limit without credentials or owner files.
# ABOUTME: Preserves the smaller limit for ordinary native calls and checks declared edit field bounds.
import json
from pathlib import Path
import subprocess
import sys
import unittest


class MemoryAlgorithmEditRPCTests(unittest.TestCase):
    def request(self, view, size):
        arguments = {'view': view, 'target': '/api/algorithm-tab/file',
            'authorization': '', 'cookie': '', 'observation': {'id': 'operational-rules', 'content': 'x' * size}}
        result = subprocess.run([sys.executable, '-m', 'lifeos_hook_bridge.memory_rpc', '--configuration',
            str(Path('/tmp/lifeos-algorithm-rpc-absent-configuration.json'))],
            input=json.dumps({'operation': 'pulse_http', 'arguments': arguments}), capture_output=True, text=True, timeout=10)
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        return json.loads(result.stdout)

    def test_declared_edit_below_source_limit_reaches_anonymous_refusal(self):
        result = self.request('algorithm_edit', 200000)
        self.assertIn('status', result, result)
        self.assertEqual(result['status'], 401)

    def test_declared_edit_above_source_limit_returns_a_bounded_request_refusal(self):
        result = self.request('algorithm_edit', 300000)
        self.assertIn('status', result, result)
        self.assertEqual(result['status'], 400)

    def test_ordinary_native_http_retains_its_smaller_transport_limit(self):
        result = self.request('life', 200000)
        self.assertEqual(result['code'], 'EWRITE_FAILED')
        self.assertEqual(result['message'], 'The native memory request exceeds the input limit')
