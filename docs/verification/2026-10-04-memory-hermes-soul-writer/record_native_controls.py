# ABOUTME: Records actual Hermes soul processes and their synthetic sources.
# ABOUTME: Keeps source bytes, process output, and test outcomes without replacing native results.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_hermes_soul_writer import MemoryHermesSoulWriterTests


def snapshot(test):
    if not hasattr(test, 'root'):
        if hasattr(test, 'fixture') and hasattr(test.fixture, 'root'):
            test.root = test.fixture.root
        else:
            return {}
    registry = test.root / "LIFEOS/MEMORY/STATE/memory-access.sqlite"
    result = {}
    for directory in ('LIFEOS/USER/HEALTH', 'LIFEOS/USER/CONDUIT', 'LIFEOS/USER/FINANCES',
                      'LIFEOS/USER/CACHE', 'LIFEOS/MEMORY/STATE', 'LIFEOS/USER/TELOS', 'LIFEOS/USER/PRINCIPAL', 'LIFEOS/USER/DIGITAL_ASSISTANT', 'LIFEOS/USER/WORK', 'LIFEOS/PULSE'):
        for path in (test.root / directory).rglob('*'):
            if path.suffix in {'.json', '.md', '.yaml', '.toml'} and path.is_file() and not path.is_symlink() and not (registry.exists() and path.samefile(registry)):
                result[str(path.relative_to(test.root))] = {'content': path.read_text(),
                    'mode': oct(path.stat().st_mode & 0o777)}
    projects = test.root / 'LIFEOS/USER/PROJECTS.md'
    if projects.is_file() and not projects.is_symlink():
        result['LIFEOS/USER/PROJECTS.md'] = {'content': projects.read_text(), 'mode': oct(projects.stat().st_mode & 0o777)}
    path = test.root / '.env'
    if path.is_file() and not path.is_symlink() and not (registry.exists() and path.samefile(registry)):
        result['.env'] = {'content': path.read_text(), 'mode': oct(path.stat().st_mode & 0o777)}
    for name in ('soul', 'context'):
        path = getattr(test, name, None)
        if isinstance(path, Path) and path.is_file() and not path.is_symlink():
            result['hermes-output/' + name] = {'content': path.read_text(), 'mode': oct(path.stat().st_mode & 0o777)}
    return result


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    native_run = subprocess.run
    events = []

    def run(*args, **kwargs):
        result = native_run(*args, **kwargs)
        command = args[0] if args else kwargs.get('args', [])
        if command and (Path(command[0]).name == 'bun' or any(str(value).endswith('memory_hermes_soul_process.py') for value in command)):
            events.append({'command': command, 'status': result.returncode,
                           'stdout': result.stdout, 'stderr': result.stderr})
        return result

    subprocess.run = run
    count = 0
    try:
        cases = [(cls, name) for cls in (MemoryHermesSoulWriterTests,)
                 for name in unittest.defaultTestLoader.getTestCaseNames(cls)]
        for cls, name in cases:
            test = cls(name)
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
            (destination / (cls.__name__ + '-' + name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
            if not result.wasSuccessful() or result.skipped:
                raise RuntimeError('Recorded evidence control fails: ' + name)
            count += 1
    finally:
        subprocess.run = native_run
    print(f'Recorded {count} passing Hermes soul controls')


if __name__ == '__main__':
    main()
