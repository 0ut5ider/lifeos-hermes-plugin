# ABOUTME: Observes actual native Life rendering before changing synthetic sources or owner authority.
# ABOUTME: Checks that the authenticated preference operation withholds the rendered response.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration

configuration = MemoryConfiguration(Path(sys.argv[1]))
mode = sys.argv[2]
target = sys.argv[3] if len(sys.argv) > 3 else '/api/life/home'
root = Path(configuration.load()['root'])
original = NativeMemory._native
rendered = False


def observe(memory, action, **arguments):
    global rendered
    result = original(memory, action, **arguments)
    if action in ('life_view', 'life_health_view', 'life_finance_view', 'life_work_view', 'life_business_view'):
        rendered = True
        if mode == 'authority': configuration.update(lambda value: value['accounts'].clear())
        elif mode == 'source':
            if target == '/api/life/business':
                path = root / 'LIFEOS/USER/WORK/YOUR_COMPANIES/synthetic-company/REVENUE/2026-10.md'
                path.write_text(path.read_text().replace('SyntheticCurrentRevenue', 'SyntheticChangedRevenue'))
            elif target == '/api/life/work':
                path = root / 'LIFEOS/USER/PROJECTS.md'
                path.write_text(path.read_text().replace('SyntheticWorkProject', 'SyntheticChangedWorkProject'))
            elif target == '/api/life/finances':
                path = root / 'LIFEOS/USER/FINANCES/ACCOUNTS.md'
                path.write_text(path.read_text().replace('SyntheticAccount', 'SyntheticChangedAccount'))
            elif target == '/api/life/health':
                path = root / 'LIFEOS/USER/HEALTH/CONDITIONS.md'
                path.write_text(path.read_text().replace('SyntheticHealthCondition', 'SyntheticHealthChangedCondition'))
            else:
                path = root / 'LIFEOS/USER/TELOS/GOALS.md'
                path.write_text(path.read_text().replace('SyntheticLifeCurrentGoal', 'SyntheticLifeChangedGoal'))
        elif mode == 'entry':
            (root / 'LIFEOS/USER/HEALTH/lab_results_2026-10-03.pdf').write_bytes(b'%PDF-Synthetic changed lab metadata')
        elif mode == 'session':
            path = root / 'LIFEOS/MEMORY/STATE/work.json'
            path.write_text(path.read_text().replace('SyntheticWorkSession', 'SyntheticChangedSession'))
        elif mode == 'created':
            (root / 'LIFEOS/USER/TELOS/TELOS.md').write_text('## Current State\n**focus:** Synthetic added focus\n')
        elif mode == 'report':
            (root / 'LIFEOS/USER/WORK/YOUR_COMPANIES/synthetic-company/REVENUE/2026-11.md').write_text(
                '## Summary\nSynthetic newer report\n')
    return result


NativeMemory._native = observe
preferences = MemoryPreferences(configuration.path, root, Path(sys.executable),
    Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py')
try:
    result = preferences.life_response(target, account='dashboard:basic:synthetic-owner')
except (PermissionError, RuntimeError, OSError, ValueError):
    print(json.dumps({'rendered': rendered, 'withheld': True}))
else:
    print(json.dumps({'rendered': rendered, 'withheld': False, 'result': result}))
