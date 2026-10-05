# ABOUTME: Experiment 1 for the PR 3 follow-up review: bytecode cache in the component directory.
# ABOUTME: Shows that a planted __pycache__ file runs instead of the hash-verified source.
import importlib._bootstrap_external as ext
import importlib.util
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, '/tmp/pr3review/src')
from lifeos_hook_bridge.memory_preferences import load_sharing_component, SHARING_COMPONENT_SHA256

REVIEWED = Path('/tmp/pr3review/src/optional/lifeos-memory-sharing/memory_sharing.py')
EVIL = "PLANTED = True\nclass MemorySharing:\n    def __init__(self, *a, **k): print('PLANTED CODE RAN')\n"


def component(name):
    base = Path('/tmp/pr3review/exp1') / name
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, mode=0o700)
    os.chmod(base, 0o700)
    shutil.copyfile(REVIEWED, base / 'memory_sharing.py')
    os.chmod(base / 'memory_sharing.py', 0o600)
    cache = base / '__pycache__'
    cache.mkdir(mode=0o700)
    return base, Path(importlib.util.cache_from_source(str(base / 'memory_sharing.py')))


code = compile(EVIL, 'memory_sharing.py', 'exec')

# Variant A: unchecked hash-based pyc. The loader never compares it with the source.
base, pyc = component('unchecked')
pyc.write_bytes(ext._code_to_hash_pyc(code, b'\0' * 8, checked=False))
module = load_sharing_component(base)
print('A unchecked-hash pyc: PLANTED' if getattr(module, 'PLANTED', False) else 'A: reviewed source ran')

# Variant B: timestamp pyc whose header copies the reviewed source mtime and size.
base, pyc = component('timestamp')
info = (base / 'memory_sharing.py').stat()
pyc.write_bytes(ext._code_to_timestamp_pyc(code, int(info.st_mtime), info.st_size))
module = load_sharing_component(base)
print('B timestamp pyc: PLANTED' if getattr(module, 'PLANTED', False) else 'B: reviewed source ran')

# Variant C: does the loader write a __pycache__ into the component directory on a normal load?
base = Path('/tmp/pr3review/exp1/fresh')
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True, mode=0o700)
shutil.copyfile(REVIEWED, base / 'memory_sharing.py'); os.chmod(base / 'memory_sharing.py', 0o600)
old = os.umask(0o002)
try:
    load_sharing_component(base)
finally:
    os.umask(old)
cache = base / '__pycache__'
print('C __pycache__ created:', cache.exists(), 'mode', oct(cache.stat().st_mode & 0o777) if cache.exists() else None,
      'under umask 002')
