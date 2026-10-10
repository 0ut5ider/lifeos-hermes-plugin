# ABOUTME: Characterizes admitted JSON inputs in the actual native Hermes health reader.
# ABOUTME: Preserves absent, invalid, scalar, array, and object state behavior.
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = Path(os.environ['LIFEOS_MEMORY_SOURCE'])


class NativeHermesHealthSourcesTests(unittest.TestCase):
    def test_native_reader_accepts_only_json_objects(self):
        values = [None, 'invalid', 'null', 'true', '42', '[]',
            json.dumps({'active_agents': 2, 'platforms': {'discord': {'state': 'connected'}}})]
        with tempfile.TemporaryDirectory() as directory:
            program = ('import {checkHermesHealth} from '
                + json.dumps(str(SOURCE / 'LIFEOS/HERMES/Health.ts')) + ';'
                'const inputs: (string|null)[] = ' + json.dumps(values) + ';'
                'console.log(JSON.stringify(inputs.map(value=>checkHermesHealth({home:'
                + json.dumps(directory) + ',installed:true,read:path=>path.endsWith("gateway_state.json")?value:null}))));')
            result = subprocess.run(['bun', '--no-install', '-e', program],
                capture_output=True, text=True, timeout=15)
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), len(values))
        for row in rows[:-1]:
            self.assertIsNone(row['pid'])
            self.assertIsNone(row['activeAgents'])
            self.assertEqual(row['platforms'], [])
        self.assertEqual(rows[-1]['activeAgents'], 2)
        self.assertEqual(rows[-1]['platforms'], [{'name': 'discord', 'state': 'connected',
            'errorCode': None, 'errorMessage': None}])


if __name__ == '__main__':
    unittest.main()
