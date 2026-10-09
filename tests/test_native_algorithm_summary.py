# ABOUTME: Characterizes actual native incremental summary generation when inference cannot run.
# ABOUTME: Records real child arguments and preserves the native failure result without model responses.
import json
import os
from pathlib import Path
import subprocess
import unittest
import test_memory_algorithm_summary as summary_fixture
import test_memory_algorithm_tab as fixture


class NativeAlgorithmSummaryTests(unittest.TestCase):
    def test_native_failed_inference_preserves_absent_cache_and_requested_levels(self):
        profile = fixture.MemoryAlgorithmTabTests()
        profile.setUp()
        self.addCleanup(profile.doCleanups)
        profile.seed()
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/PULSE/modules/algorithm-tab.ts'
        program = profile.fixture.home / 'native-summary-characterization.ts'
        program.write_text(control.read_text() + '\n' + '''
const observed: string[][] = [];
const actualSpawn = Bun.spawn;
Bun.spawn = (...args: Parameters<typeof Bun.spawn>) => {
  observed.push(args[0]);
  return actualSpawn(...args);
};
await regenerateAll(true);
console.log(JSON.stringify({observed, generating: state.generating, lastAttempt: state.lastAttempt,
  cacheExists: await Bun.file(STATE_PATH).exists()}));
''')
        result = subprocess.run(['bun', '--no-install', str(program)], capture_output=True, text=True,
            timeout=40, env=dict(os.environ, HOME=str(profile.fixture.home), CLAUDE_CONFIG_DIR=str(profile.root)))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        evidence = Path(__file__).resolve().parents[1] / 'docs/verification/2026-10-08-remaining-reader-audit/native-algorithm-summary-observation.json'
        evidence.write_text(json.dumps({'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
        lines = result.stdout.splitlines()
        observation = json.loads(lines[-1])
        self.assertFalse(observation['generating'])
        self.assertFalse(observation['lastAttempt']['ok'])
        self.assertFalse(observation['cacheExists'])
        levels = {row[row.index('--level') + 1] for row in observation['observed']}
        self.assertEqual(levels, {'low', 'high'})
        self.assertTrue(all('Inference.ts' in row[1] for row in observation['observed']))
        self.assertTrue(any('regeneration pass done (with failures)' in line for line in lines))
        self.assertEqual(sum(line.startswith('[algorithm-tab] inference(') for line in lines[:-1]),
            len(observation['observed']))
        self.assertIn('Module not found', result.stdout)


    def test_prepared_native_plan_matches_original_child_prompts(self):
        profile = summary_fixture.MemoryAlgorithmSummaryTests()
        profile.setUp()
        self.addCleanup(profile.doCleanups)
        prepared = profile.prepare()
        tools = profile.root / 'LIFEOS/TOOLS'
        public = tools.resolve()
        tools.unlink()
        tools.mkdir()
        for entry in public.iterdir():
            if entry.name != 'Inference.ts':
                (tools / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
        self.assertFalse((tools / 'Inference.ts').exists())
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) / 'LIFEOS/PULSE/modules/algorithm-tab.ts'
        program = profile.owner.fixture.home / 'native-summary-plan-characterization.ts'
        # Observe each original spawn request without replacing native planning or output.
        program.write_text(control.read_text() + '\n' + """
const observed: string[][] = [];
const actualSpawn = Bun.spawn;
Bun.spawn = (...args: Parameters<typeof Bun.spawn>) => {
  observed.push(args[0]);
  return actualSpawn(...args);
};
await regenerateAll(true);
console.log(JSON.stringify({observed, hash: await chainHash()}));
""")
        environment = dict(os.environ, HOME=str(profile.owner.fixture.home), CLAUDE_CONFIG_DIR=str(profile.root),
            LIFEOS_MEMORY_CONFIGURATION_REVISION='0' * 64)
        result = subprocess.run(['bun', '--no-install', str(program)], capture_output=True, text=True,
            timeout=60, env=environment)
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        observation = json.loads(result.stdout.splitlines()[-1])
        actual = [{'level': row[row.index('--level') + 1], 'system': row[-2], 'user': row[-1]}
            for row in observation['observed']]
        expected = [{key: row[key] for key in ('level', 'system', 'user')} for row in prepared['plan']['files']]
        expected.append(prepared['plan']['overview'])
        self.assertEqual(actual, expected)
        self.assertEqual(observation['hash'], prepared['plan']['hash'])
        self.assertFalse(profile.cache.exists())
