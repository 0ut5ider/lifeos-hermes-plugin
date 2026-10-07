# ABOUTME: Checks native evaluation fire-state publication during concurrent hook execution.
# ABOUTME: Widens the actual file-publication interval without substituting evaluation results.
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native source and Bun are required')
class NativeEvaluationConcurrencyTests(unittest.TestCase):
    def test_concurrent_publications_use_separate_temporary_files(self):
        with tempfile.TemporaryDirectory(prefix='evaluation-publication-') as directory:
            home = Path(directory)
            runner = home / '.claude/LIFEOS/TOOLS/ConfigEvalOnChange.ts'
            runner.parent.mkdir(parents=True)
            # This control measures hook state publication. Real suite execution has separate controls.
            runner.write_text('// ABOUTME: Terminates a detached fixture runner.\n'
                              '// ABOUTME: Leaves evaluation output unclaimed by this state-publication control.\n'
                              'process.exit(0);\n')
            preload = home / 'publication-delay.cjs'
            preload.write_text('''// ABOUTME: Widens the native fire-state publication interval for a race control.
// ABOUTME: Writes the actual file before delaying the calling process.
const fs = require('node:fs');
const original = fs.writeFileSync;
fs.writeFileSync = function(path, ...args) {
  const result = original.call(this, path, ...args);
  if (/config-eval-state\\.json.*\\.tmp$/.test(String(path))) {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
  }
  return result;
};
''')
            env = {**os.environ, 'HOME': str(home)}
            for key in ('CLAUDE_CODE_FORK_SUBAGENT', 'LIFEOS_SUBAGENT', 'CLAUDE_AGENT_ID'):
                env.pop(key, None)
            payload = json.dumps({'tool_name': 'Edit', 'tool_input': {'file_path': '/fixture/change.hook.ts'}})

            def invoke(index):
                return subprocess.run(['bun', '--preload', str(preload), str(Path(SOURCE) / 'hooks/ConfigEvalFire.hook.ts')],
                    env=env, input=payload, text=True, capture_output=True, timeout=15)

            with ThreadPoolExecutor(max_workers=16) as pool:
                results = list(pool.map(invoke, range(16)))
            evidence = os.environ.get('LIFEOS_EVALUATION_CONCURRENCY_EVIDENCE')
            if evidence:
                path = Path(evidence)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps([{'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
                                           for r in results], indent=2) + '\n')
            self.assertEqual([(r.returncode, r.stdout, r.stderr) for r in results], [(0, '', '')] * len(results))
            state = runner.parent.parent / 'MEMORY/OBSERVABILITY/config-eval-state.json'
            self.assertIsInstance(json.loads(state.read_text())['last_fire'], str)
            self.assertEqual(list(state.parent.glob('config-eval-state.json*.tmp')), [])
