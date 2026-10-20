# ABOUTME: Probes dashboard_options parsing edge cases against live sleeping processes.
# ABOUTME: Prints each argv and the parsed result or the refusal.
import subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
from optional.lifeos_release_manager.consumer_scan import dashboard_options, _role
cases = [
    ['serve', '--host', '0.0.0.0', '--port', '9119'],
    ['-p', 'default', 'dashboard', '--port', '9119', '--host', '0.0.0.0', '--open-profile', 'work'],
    ['dashboard', '--ho', '0.0.0.0'],
    ['dashboard', '--host', '0.0.0.0', '--host', '127.0.0.1'],
    ['dashboard', '--host=::'],
    ['dashboard', '--host', '[::1]'],
    ['dashboard', '--host', '%h'],
    ['dashboard', '--host='],
    ['dashboard', '--port', '+9119'],
    ['dashboard', '--port', '９１１９'],
    ['dashboard', '--host', '-x'],
    ['dashboard', '--host', '127.0.0.1'],
]
for args in cases:
    p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)', *args])
    try:
        deadline = time.monotonic() + 5
        while not Path('/proc', str(p.pid), 'cmdline').read_bytes() and time.monotonic() < deadline:
            time.sleep(0.01)
        try:
            r = dashboard_options(p.pid)
        except Exception as e:
            r = type(e).__name__ + ': ' + str(e)[:60]
        role = _role(Path('/proc', str(p.pid), 'cmdline').read_bytes())
        print(args, role, '->', r)
    finally:
        p.kill(); p.wait()
