# ABOUTME: Probes dashboard_options from 11e98e5d against every real Hermes dashboard and serve option.
# ABOUTME: Spawns sleeping processes with the given argv and prints the result or refusal.
import subprocess, sys, time
sys.path.insert(0, '/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
from optional.lifeos_release_manager.consumer_scan import dashboard_options
cases = [
 ['dashboard'], ['serve'],
 ['dashboard','--insecure','--skip-build','--isolated','--no-open','--tui','--stop','--status'],
 ['serve','--no-open','--ssh-session-token-file','/run/user/1000/tok','--ssh-owner-nonce','abc-DEF_123'],
 ['dashboard','--open-profile','work','--port','9119','--host','127.0.0.1'],
 ['-p','default','serve','--port','9119','--host','0.0.0.0','--open-profile','work','--ssh-owner-nonce','n1'],
 ['dashboard','-h'], ['dashboard','--help'],
 ['dashboard','--h','x'], ['dashboard','--p','9200'], ['dashboard','--po','9200'], ['serve','--hos=0.0.0.0'],
 ['dashboard','--s'], ['dashboard','--i'], ['dashboard','--o','x'], ['serve','--ssh','x'],
 ['dashboard','--host','localhost'], ['dashboard','--port','9119'], ['dashboard','--host','127.0.0.1'],
 ['--profile','work','dashboard','--port','9200'], ['dashboard','--', '--port'],
]
for c in cases:
    p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)', *c])
    time.sleep(0.15)
    try:
        r = dashboard_options(p.pid)
    except Exception as e:
        r = 'REFUSED ' + type(e).__name__
    p.kill(); p.wait()
    print(c, '->', r)
