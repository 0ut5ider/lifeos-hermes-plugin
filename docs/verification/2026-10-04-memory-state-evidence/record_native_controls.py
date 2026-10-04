# ABOUTME: Records actual state evidence processes and their synthetic JSON sources.
# ABOUTME: Keeps source bytes, process output, and test outcomes without replacing native results.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_state_evidence import MemoryStateEvidenceTests


def snapshot(test):
    if not hasattr(test, 'root'):
        return {}
    registry = test.fixture.memory.database
    result = {}
    for directory in ('LIFEOS/USER/HEALTH', 'LIFEOS/USER/CONDUIT', 'LIFEOS/USER/FINANCES',
                      'LIFEOS/USER/CACHE', 'LIFEOS/MEMORY/STATE'):
        for path in (test.root / directory).rglob('*.json'):
            if path.is_file() and not path.is_symlink() and not (registry.exists() and path.samefile(registry)):
                result[str(path.relative_to(test.root))] = {'content': path.read_text(),
                    'mode': oct(path.stat().st_mode & 0o777)}
    return result


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    native_run = subprocess.run
    events = []

    def run(*args, **kwargs):
        result = native_run(*args, **kwargs)
        command = args[0] if args else kwargs.get('args', [])
        if command and (command[0] == 'bun' or any(str(value).endswith('memory_evidence_process.py') for value in command)):
            events.append({'command': command, 'status': result.returncode,
                           'stdout': result.stdout, 'stderr': result.stderr})
        return result

    subprocess.run = run
    count = 0
    try:
        for name in unittest.defaultTestLoader.getTestCaseNames(MemoryStateEvidenceTests):
            test = MemoryStateEvidenceTests(name)
            events = []
            result = unittest.TestResult()
            setup = test.setUp
            cleanup = test.doCleanups
            captured = {}

            def before():
                setup()
                captured['before'] = snapshot(test)

            def after():
                try:
                    captured['after'] = snapshot(test)
                finally:
                    cleanup()

            test.setUp = before
            test.doCleanups = after
            test.run(result)
            record = {'case': name, 'native_source': os.environ['LIFEOS_MEMORY_SOURCE'],
                      'sources': captured, 'events': events,
                      'failures': [{'case': str(case), 'text': output} for case, output in result.failures],
                      'errors': [{'case': str(case), 'text': output} for case, output in result.errors],
                      'skips': [{'case': str(case), 'reason': reason} for case, reason in result.skipped]}
            (destination / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
            if not result.wasSuccessful() or result.skipped:
                raise RuntimeError('Recorded evidence control fails: ' + name)
            count += 1
    finally:
        subprocess.run = native_run
    print(f'Recorded {count} passing state evidence controls')


if __name__ == '__main__':
    main()
