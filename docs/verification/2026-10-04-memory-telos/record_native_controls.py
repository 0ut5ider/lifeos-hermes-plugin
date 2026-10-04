# ABOUTME: Records actual native state and summary calls from the existing synthetic regressions.
# ABOUTME: Retains source text and artifact output without substituting native results.
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_state import MemoryStateTests
from test_memory_telos import MemoryTelosTests


def snapshot(test):
    sources = {}
    for path in test.telos.rglob('*.md'):
        if path.is_file() and not path.is_symlink() and path != test.output:
            sources[str(path.relative_to(test.root))] = path.read_text()
    identity = test.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
    if identity.is_file() and not identity.is_symlink():
        sources[str(identity.relative_to(test.root))] = identity.read_text()
    artifact = None
    if (test.output.is_file() and not test.output.is_symlink()
            and not test.output.samefile(test.fixture.fixture.memory.database)):
        data = test.output.read_bytes()
        artifact = {'sha256': hashlib.sha256(data).hexdigest(), 'content': data.decode(),
                    'mode': oct(test.output.stat().st_mode & 0o777)}
    return {'sources': sources, 'artifact': artifact}


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    for cls in (MemoryStateTests, MemoryTelosTests):
        real_call = cls.call
        real_process = cls.process
        events = []

        def call(test, *arguments, **options):
            before = snapshot(test)
            result = real_call(test, *arguments, **options)
            events.append({'kind': 'native_cli', 'arguments': arguments, 'options': options,
                'before': before, 'status': result.returncode, 'stdout': result.stdout,
                'stderr': result.stderr, 'after': snapshot(test)})
            return result

        def process(test, mode):
            before = snapshot(test)
            result = real_process(test, mode)
            events.append({'kind': 'native_interleaving', 'mode': mode, 'before': before,
                'status': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
                'after': snapshot(test)})
            return result

        cls.call = call
        cls.process = process
        try:
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                events = []
                result = unittest.TestResult()
                cls(name).run(result)
                record = {'case': cls.__name__ + '.' + name,
                    'native_source': os.environ['LIFEOS_MEMORY_SOURCE'], 'events': events,
                    'failures': result.failures, 'errors': result.errors, 'skips': result.skipped}
                (destination / (cls.__name__ + '-' + name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
                assert result.wasSuccessful() and not result.skipped, name
                count += 1
        finally:
            cls.call = real_call
            cls.process = real_process
    print(f'Recorded {count} passing native regression controls')


if __name__ == '__main__':
    main()
