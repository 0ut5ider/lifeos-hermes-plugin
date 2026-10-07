# ABOUTME: Measures real Hermes lasting-store behavior under supplied profile configuration.
# ABOUTME: Captures expected configuration warnings and retained file bytes without replacing native results.
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys

from hermes_constants import get_hermes_home
import tools.memory_tool as memory_tool
from tools.memory_tool import get_builtin_memory_store_flags, load_on_disk_store
from tools.registry import registry

arguments = json.loads(sys.stdin.read())
home = get_hermes_home()
paths = [home / 'memories/MEMORY.md', home / 'memories/USER.md']
before = [path.read_bytes() for path in paths]
warnings = io.StringIO()
with redirect_stderr(warnings):
    flags = get_builtin_memory_store_flags()
    store = load_on_disk_store()
    result = registry.dispatch('memory', {'action': 'add', 'target': arguments['target'],
        'content': 'Synthetic attempted fallback write.'}, store=store) if arguments['operation'] == 'write' else None
    if isinstance(result, str):
        result = json.loads(result)
print(json.dumps({'module': memory_tool.__file__, 'flags': flags, 'store_flags': [store.target_enabled('memory'), store.target_enabled('user')],
                  'result': result, 'unchanged': [path.read_bytes() for path in paths] == before,
                  'warnings': warnings.getvalue()}))
