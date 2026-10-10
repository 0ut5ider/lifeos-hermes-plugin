# ABOUTME: Exercises Algorithm prompt transport through real native inference subprocesses.
# ABOUTME: Measures complete ASCII and UTF-8 input delivery to a rejecting diagnostic child without model output.
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NativeAlgorithmPromptTransportTests(unittest.TestCase):
    def test_complete_large_prompts_reach_native_child_without_argument_overflow(self):
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        module = (source / 'LIFEOS/PULSE/modules/algorithm-tab.ts').read_text()
        helper = module.split('async function inference(level:', 1)[1].split('\nconst OVERVIEW_PROMPT', 1)[0]
        helper = 'async function inference(level:' + helper
        native = source / 'LIFEOS/TOOLS/Inference.ts'
        for level, system, user in [('high', 'Synthetic transport system.', 'a' * 200_000),
                ('low', 'Synthetic transport system.', '\u20ac' * 60_000),
                ('high', 's' * 200_000, 'Synthetic transport user.')]:
            with self.subTest(level=level, system_bytes=len(system.encode()), user_bytes=len(user.encode())):
                with tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    child = home / 'claude'
                    child.write_text('#!/usr/bin/python3\n'
                        'import json, os, pathlib, sys\n'
                        'payload = sys.stdin.buffer.read()\n'
                        'args = sys.argv[1:]\n'
                        'system = (pathlib.Path(args[args.index("--system-prompt-file") + 1]).read_bytes()\n'
                        '    if "--system-prompt-file" in args else args[args.index("--system-prompt") + 1].encode())\n'
                        'pathlib.Path(os.environ["TRANSPORT_OBSERVATION"]).write_text(json.dumps({\n'
                        '    "user_bytes": len(payload), "system_bytes": len(system),\n'
                        '    "output_format": args[args.index("--output-format") + 1],\n'
                        '    "system_file": args[args.index("--system-prompt-file") + 1]\n'
                        '        if "--system-prompt-file" in args else None}))\n'
                        'sys.exit(7)\n')
                    child.chmod(0o700)
                    observation = home / 'transport.json'
                    program = home / 'transport.ts'
                    program.write_text('import { inference as nativeInference } from ' + json.dumps(str(native)) + ';\n'
                        'const INFERENCE = ' + json.dumps(str(native)) + ';\n'
                        'const MODULE_NAME = "algorithm-tab";\n' + helper + '\n'
                        'const result = await inference(' + json.dumps(level) + ', ' + json.dumps(system)
                        + ', ' + json.dumps(user) + ', 5000, true);\n'
                        'console.log(JSON.stringify({result}));\n')
                    environment = {'HOME': str(home), 'PATH': str(home) + ':' + str(Path(shutil.which('bun')).parent)
                        + ':/usr/bin:/bin', 'TRANSPORT_OBSERVATION': str(observation),
                        'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
                    result = subprocess.run(['bun', '--no-install', str(program)], env=environment,
                        capture_output=True, text=True, timeout=15)
                    self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout.splitlines()[-1]), {'result': None})
                    actual = json.loads(observation.read_text())
                    system_file = actual.pop('system_file')
                    self.assertEqual(actual, {
                        'user_bytes': len(user.encode()), 'system_bytes': len(system.encode()), 'output_format': 'json'})
                    if len(system.encode()) > 100_000:
                        self.assertIsNotNone(system_file)
                        self.assertFalse(Path(system_file).exists())
                    else:
                        self.assertIsNone(system_file)
