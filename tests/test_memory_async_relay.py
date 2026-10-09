# ABOUTME: Exercises asynchronous native relay limits against real child processes.
# ABOUTME: Checks response validation, bounded output, cancellation, and private command configuration.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


class MemoryAsyncRelayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='lifeos-async-relay-')
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.source = Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/TOOLS/lib/MemoryAccess.ts'
        self.configuration = self.home / '.claude/LIFEOS/USER/CONFIG/memory-access.json'
        self.configuration.parent.mkdir(parents=True)
        self.child = self.home / 'relay-process.py'
        self.child.write_text('''# ABOUTME: Produces declared fault responses for an isolated relay test.
# ABOUTME: Reads the actual child request and tests pipe limits and cancellation.
import json
import sys
import time

request = json.load(sys.stdin)
mode = sys.argv[1]
response = {'status': 200, 'body': json.dumps(request), 'headers': [['content-type', 'application/json']]}
if mode == 'nonzero': sys.exit(2)
elif mode == 'stdout': sys.stdout.write('x' * (4 * 1024 * 1024 + 1))
elif mode == 'stderr': sys.stderr.write('x' * (4 * 1024 * 1024 + 1))
elif mode == 'cancel': time.sleep(60)
elif mode == 'invalid-status': response['status'] = 201
elif mode == 'invalid-body': response['body'] = {'unexpected': True}
elif mode == 'invalid-header': response['headers'] = [['location', 'https://outside.invalid']]
elif mode == 'malformed': sys.stdout.write('{synthetic malformed response')
if mode not in ('stdout', 'stderr', 'malformed'): print(json.dumps(response))
''')
        self.program = self.home / 'relay.ts'
        self.program.write_text('import {memoryHTTPResponseAsync} from ' + json.dumps(str(self.source)) + ';\n'
            'const cancellation=new AbortController();\n'
            'if(process.argv[2]==="aborted")cancellation.abort();\n'
            'const timer=process.argv[2]==="cancel"?setTimeout(()=>cancellation.abort(),30):null;\n'
            'try{const response=await memoryHTTPResponseAsync(new Request("http://127.0.0.1/api/algorithm",\n'
            ' {signal:cancellation.signal,headers:{authorization:"Bearer synthetic",cookie:"synthetic-cookie"}}),\n'
            ' "life","/api/algorithm");\n'
            'console.log(JSON.stringify({accepted:true,status:response.status,cache:response.headers.get("cache-control"),body:await response.json()}));\n'
            '}catch{console.log(JSON.stringify({accepted:false}));}\n'
            'finally{if(timer!==null)clearTimeout(timer);}\n')

    def run_process(self, mode, *, permissions=0o600, signal=''):
        self.configuration.write_text(json.dumps({'version': 1, 'command': [sys.executable, str(self.child), mode]}))
        self.configuration.chmod(permissions)
        result = subprocess.run(['bun', '--no-install', str(self.program), signal], capture_output=True,
            text=True, timeout=10, env=dict(os.environ, HOME=str(self.home)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_actual_child_receives_only_declared_http_operation_and_credentials(self):
        observed = self.run_process('valid')
        self.assertEqual(observed, {'accepted': True, 'status': 200, 'cache': 'no-store', 'body': {
            'operation': 'pulse_http', 'arguments': {'view': 'life', 'target': '/api/algorithm',
                'authorization': 'Bearer synthetic', 'cookie': 'synthetic-cookie'}}})

    def test_invalid_child_responses_and_pipe_overflow_refuse(self):
        for mode in ('nonzero', 'stdout', 'stderr', 'invalid-status', 'invalid-body', 'invalid-header', 'malformed'):
            with self.subTest(mode=mode):
                self.assertEqual(self.run_process(mode), {'accepted': False})

    def test_cancellation_stops_sleeping_child_and_already_aborted_request(self):
        for signal in ('cancel', 'aborted'):
            with self.subTest(signal=signal):
                started = time.monotonic()
                self.assertEqual(self.run_process('cancel', signal=signal), {'accepted': False})
                self.assertLess(time.monotonic() - started, 5)

    def test_public_or_redirected_command_configuration_refuses(self):
        self.assertEqual(self.run_process('valid', permissions=0o644), {'accepted': False})
        outside = self.home / 'outside-configuration.json'
        self.configuration.rename(outside)
        self.configuration.symlink_to(outside)
        result = subprocess.run(['bun', '--no-install', str(self.program)], capture_output=True, text=True,
            timeout=10, env=dict(os.environ, HOME=str(self.home)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'accepted': False})


if __name__ == '__main__':
    unittest.main()
