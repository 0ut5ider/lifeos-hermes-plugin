# ABOUTME: Records actual native freshness CLI, library, and authenticated HTTP controls.
# ABOUTME: Retains synthetic source text and real responses without substituting renderer results.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests'))
from test_memory_freshness import MemoryFreshnessTests
from test_memory_freshness_consistency import MemoryFreshnessConsistencyTests
from test_memory_freshness_relay import MemoryFreshnessRelayTests


def snapshot(test):
    if not hasattr(test, 'root'):
        return {}
    root = test.root
    registry = root / 'LIFEOS/MEMORY/STATE/memory-access.sqlite'
    sources = {}
    for directory in ('LIFEOS/USER/TELOS', 'LIFEOS/USER/PRINCIPAL', 'LIFEOS/USER/DIGITAL_ASSISTANT',
                      'LIFEOS/DOCUMENTATION'):
        for path in (root / directory).rglob('*.md'):
            if (path.is_file() and not path.is_symlink()
                    and not (registry.exists() and path.samefile(registry))):
                sources[str(path.relative_to(root))] = path.read_text()
    return sources


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    real_run = subprocess.run
    real_request = httpx.Client.request
    active = None
    events = []

    def run(*args, **kwargs):
        result = real_run(*args, **kwargs)
        command = args[0] if args else kwargs.get('args', [])
        if active is not None and command and command[0] == 'bun':
            events.append({'kind': 'native_process', 'command': command, 'status': result.returncode,
                           'stdout': result.stdout, 'stderr': result.stderr})
        return result

    def request(client, method, url, *args, **kwargs):
        response = real_request(client, method, url, *args, **kwargs)
        if active is not None and str(url).startswith(getattr(active, 'native', 'missing://')):
            events.append({'kind': 'native_http', 'method': method, 'url': str(url),
                           'status': response.status_code, 'body': response.text,
                           'cache-control': response.headers.get('cache-control')})
        return response

    subprocess.run = run
    httpx.Client.request = request
    count = 0
    try:
        for cls in (MemoryFreshnessTests, MemoryFreshnessRelayTests, MemoryFreshnessConsistencyTests):
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                active = cls(name)
                events = []
                result = unittest.TestResult()
                real_setup = active.setUp
                real_cleanup = active.doCleanups
                captured = {}

                def setup():
                    real_setup()
                    captured['before'] = snapshot(active)

                def cleanup():
                    captured['after'] = snapshot(active)
                    return real_cleanup()

                active.setUp = setup
                active.doCleanups = cleanup
                active.run(result)
                record = {'case': cls.__name__ + '.' + name, 'native_source': os.environ['LIFEOS_MEMORY_SOURCE'],
                    'sources': captured, 'events': events,
                    'failures': [{'case': str(test), 'text': output} for test, output in result.failures],
                    'errors': [{'case': str(test), 'text': output} for test, output in result.errors],
                    'skips': [{'case': str(test), 'reason': reason} for test, reason in result.skipped]}
                (destination / (cls.__name__ + '-' + name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
                if not result.wasSuccessful() or result.skipped:
                    raise RuntimeError('The recorded native control fails: ' + name)
                count += 1
    finally:
        subprocess.run = real_run
        httpx.Client.request = real_request
    print(f'Recorded {count} passing native freshness controls')


if __name__ == '__main__':
    main()
