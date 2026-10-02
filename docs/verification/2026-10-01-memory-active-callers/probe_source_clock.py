# ABOUTME: Compares Python source display clocks with the native Bun filesystem Date.
# ABOUTME: Uses temporary files with exact timestamps around millisecond boundaries.
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile

from lifeos_hook_bridge.memory_sources import _source_time

with tempfile.TemporaryDirectory(prefix='native-source-clock-') as directory:
    paths = []
    for seconds in (1, 1700000000, 1790905907, 2000000000):
        for milliseconds in (0, 1, 387, 999):
            for offset in (0, 1, 128, 500_000, 999_000, 999_400, 999_600, 999_800, 999_900, 999_999):
                path = Path(directory) / str(len(paths))
                path.write_text('Synthetic clock source')
                timestamp = seconds * 1_000_000_000 + milliseconds * 1_000_000 + offset
                os.utime(path, ns=(timestamp, timestamp))
                paths.append(path)
    worker = 'import {statSync} from "node:fs"; const paths=JSON.parse(await Bun.stdin.text()); process.stdout.write(JSON.stringify(paths.map(path=>statSync(path).mtime.toISOString())));'
    result = subprocess.run(['bun', '--no-install', '-e', worker], input=json.dumps([str(path) for path in paths]),
                            text=True, capture_output=True, check=True)
    assert not result.stderr, result.stderr
    native = json.loads(result.stdout)
    failures = []
    for path, date in zip(paths, native, strict=True):
        actual = _source_time(path.stat(), milliseconds=True)
        if datetime.fromisoformat(actual) != datetime.fromisoformat(date):
            failures.append({'nanoseconds': path.stat().st_mtime_ns, 'native': date, 'managed': actual})
    print(json.dumps({'cases': len(paths), 'failures': failures}, indent=2))
    raise SystemExit(bool(failures))
