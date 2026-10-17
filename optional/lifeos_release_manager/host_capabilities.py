# ABOUTME: Probes, in a fresh interpreter, the plugin capabilities that a Hermes source exposes to the bridge.
# ABOUTME: Checks the Python version, the patched hook names, and the middleware API version that a release qualifies.
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from .release_catalog import ReleaseRejected


PROBE = '''import json, sys
sys.path.insert(0, sys.argv[1])
result = {"python": "%d.%d" % sys.version_info[:2]}
try:
    from hermes_cli.plugins import VALID_HOOKS
    result["hooks"] = sorted(VALID_HOOKS)
except Exception as error:
    result["hooks_error"] = type(error).__name__
try:
    from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION
    result["middleware_api"] = REQUIRED_MIDDLEWARE_API_VERSION
except Exception as error:
    result["middleware_error"] = type(error).__name__
print(json.dumps(result))
'''


def probe_capabilities(python, source, entry, *, environment=None):
    """Require that ``python`` importing ``source`` exposes the interpreter and capabilities of ``entry``.

    The probe runs isolated (``-I``), so an inherited ``PYTHONPATH`` cannot substitute another Hermes,
    and without bytecode (``-B``), so it leaves the source unchanged. Returns the probe's findings.
    """
    selected = {key: value for key, value in (os.environ if environment is None else environment).items()
                if key not in {'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'}}
    try:
        result = subprocess.run([str(python), '-I', '-B', '-c', PROBE, str(Path(source))], capture_output=True,
                                text=True, env=selected, cwd=str(source), timeout=120)
        value = json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        value = None
    if not isinstance(value, dict):
        raise ReleaseRejected('The Hermes capability probe does not run with the Hermes interpreter')
    if value.get('python') != entry['python']:
        raise ReleaseRejected('LifeOS qualifies Hermes ' + entry['label'] + ' with Python ' + entry['python']
                              + ', but the Hermes interpreter is Python ' + str(value.get('python')))
    required = entry['capabilities']
    if not isinstance(value.get('hooks'), list):
        raise ReleaseRejected('Hermes does not report its plugin hook names')
    missing = sorted(set(required['hooks']) - set(value['hooks']))
    if missing:
        raise ReleaseRejected('Hermes does not offer the patched plugin hooks: ' + ', '.join(missing))
    if value.get('middleware_api') != required['middleware_api']:
        raise ReleaseRejected('Hermes does not require middleware API version ' + str(required['middleware_api']))
    return value
