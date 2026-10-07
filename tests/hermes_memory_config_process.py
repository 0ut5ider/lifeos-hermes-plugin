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
    multiplex = []
    if arguments['operation'] == 'multiplex':
        from hermes_constants import set_hermes_home_override, reset_hermes_home_override
        from agent.secret_scope import set_multiplex_active, set_secret_scope, reset_secret_scope
        secondary = home / 'profiles/secondary'
        secondary.mkdir(parents=True)
        (secondary / 'config.yaml').write_text('memory:\n  memory_enabled: true\n  user_profile_enabled: true\n')
        set_multiplex_active(True)
        try:
            for selected in (home, secondary, home):
                home_token = set_hermes_home_override(str(selected))
                secret_token = set_secret_scope({}, profile_home=str(selected))
                try:
                    selected_store = load_on_disk_store()
                    multiplex.append({'flags': get_builtin_memory_store_flags(),
                        'store_flags': [selected_store.target_enabled('memory'), selected_store.target_enabled('user')]})
                finally:
                    reset_secret_scope(secret_token)
                    reset_hermes_home_override(home_token)
        finally:
            set_multiplex_active(False)
    result = registry.dispatch('memory', {'action': 'add', 'target': arguments['target'],
        'content': 'Synthetic attempted fallback write.'}, store=store) if arguments['operation'] == 'write' else None
    if isinstance(result, str):
        result = json.loads(result)
print(json.dumps({'module': memory_tool.__file__, 'multiplex': multiplex, 'flags': flags, 'store_flags': [store.target_enabled('memory'), store.target_enabled('user')],
                  'result': result, 'unchanged': [path.read_bytes() for path in paths] == before,
                  'warnings': warnings.getvalue()}))
