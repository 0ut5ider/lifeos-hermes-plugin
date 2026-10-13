# ABOUTME: Captures the actual runtime verification subprocess result during an admitted development update.
# ABOUTME: Keeps raw command output private and preserves the frozen worker's calls and return values.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

os.umask(0o077)
job = Path(sys.argv[1])
request = json.loads((job / 'request.json').read_bytes())
sys.path.insert(0, request['runtime']['source'])
namespace = types.ModuleType('diagnostic_release_worker')
namespace.__path__ = [str(job / 'worker')]
sys.modules[namespace.__name__] = namespace
worker = importlib.import_module(namespace.__name__ + '.release_worker')
verify = worker.verify_runtime
folder = job / 'runtime-diagnostics'
folder.mkdir(mode=0o700)
receipts = []

def observe(request, **options):
    original = subprocess.run

    def capture(command, *arguments, **keywords):
        started = time.monotonic()
        result = original(command, *arguments, **keywords)
        index = len(receipts)
        for name in ('stdout', 'stderr'):
            text = getattr(result, name)
            (folder / (str(index) + '.' + name)).write_text(text or '')
        receipts.append({'arguments': [str(value) for value in command],
            'cwd': str(keywords.get('cwd', Path.cwd())),
            'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - started,
            'stdout_bytes': len((result.stdout or '').encode()),
            'stderr_bytes': len((result.stderr or '').encode()),
            'restored': options.get('restored', False)})
        (folder / 'receipt.json').write_text(json.dumps(receipts, indent=2) + '\n')
        if result.returncode != 0:
            try:
                with (folder / 'parser-probe.stdout').open('w') as stdout, (folder / 'parser-probe.stderr').open('w') as stderr:
                    probe = original([request['runtime']['python'], '-B',
                        str(Path(__file__).with_name('diagnose_parser_registration.py')),
                        request['runtime']['source'], str(folder)],
                        env=keywords.get('env'), cwd=keywords.get('cwd'),
                        stdout=stdout, stderr=stderr, timeout=45)
                (folder / 'parser-probe.exit').write_text(str(probe.returncode) + '\n')
            except Exception as error:
                (folder / 'parser-probe.error').write_text(type(error).__name__ + '\n')
        return result

    subprocess.run = capture
    try:
        return verify(request, **options)
    finally:
        subprocess.run = original

worker.verify_runtime = observe
worker.execute(job, 'apply')
