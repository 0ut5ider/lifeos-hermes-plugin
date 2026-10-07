# ABOUTME: Records native adapter processes and actual synthetic gateway requests.
# ABOUTME: Retains generated page bytes and refusal outcomes without replacing process results.
import json, os, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_pulse_adapter_inference import MemoryPulseAdapterInferenceTests

p = Path(sys.argv[1])
p.mkdir(parents=True, exist_ok=True)
original = subprocess.run
events = []
def run(*args, **kwargs):
    result = original(*args, **kwargs)
    command = args[0] if args else kwargs.get('args', [])
    if command and Path(command[0]).name == 'bun':
        events.append({'command': command, 'status': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    return result
subprocess.run = run
count = 0
try:
    for name in unittest.defaultTestLoader.getTestCaseNames(MemoryPulseAdapterInferenceTests):
        test = MemoryPulseAdapterInferenceTests(name)
        events = []
        setup, cleanup = test.setUp, test.doCleanups
        sources = {}
        def snapshot():
            root = test.fixture.root
            paths = [test.fixture.source, test.fixture.manifest, root / 'LIFEOS/PULSE/pages/synthetic.adapter.md']
            paths += list(test.fixture.data.glob('*.json'))
            return {str(path.relative_to(root)): {'content': path.read_text(), 'mode': oct(path.stat().st_mode & 0o777)}
                    for path in paths if path.is_file() and not path.is_symlink()}
        def before():
            setup()
            sources['before'] = snapshot()
        def after():
            try:
                sources['after'] = snapshot()
            finally:
                cleanup()
        test.setUp, test.doCleanups = before, after
        result = unittest.TestResult()
        test.run(result)
        record = {'case': name, 'native_source': os.environ['LIFEOS_MEMORY_SOURCE'], 'sources': sources,
                  'requests': test.received, 'events': events,
                  'errors': [{'case': str(case), 'text': output} for case, output in result.errors],
                  'failures': [{'case': str(case), 'text': output} for case, output in result.failures],
                  'skips': [{'case': str(case), 'reason': reason} for case, reason in result.skipped]}
        (p / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        if not result.wasSuccessful() or result.skipped:
            raise RuntimeError('Recorded inference control fails: ' + name)
        count += 1
finally:
    subprocess.run = original
print(f'Recorded {count} native adapter inference controls')
