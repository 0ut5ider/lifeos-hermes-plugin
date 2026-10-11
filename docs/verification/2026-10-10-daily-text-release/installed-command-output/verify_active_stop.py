# ABOUTME: Measures actual three-service draining while the native scheduler runs a selected owner job.
# ABOUTME: Restores the exact daily configuration and checks that the acceptance control groups are empty.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
os.environ.update(HOME=str(root.parent), HERMES_HOME=str(profile),
    PATH=str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    PYTHONPATH=str(stage / 'package/hermes'), TZ='America/Toronto',
    XDG_RUNTIME_DIR='/run/user/1008', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1008/bus')
sys.path[:0] = [str(profile / 'plugins'), str(stage / 'package/hermes')]
def module(name):
    return importlib.import_module('lifeos-hook-bridge.' + name)
units = json.loads((stage / 'application-units.json').read_text())['units']
services = module('profile_services').ProfileServices(profile, root, units=units)
target = root / 'LIFEOS/USER/CONFIG/PULSE.user.toml'
original = target.read_bytes()
retained = stage / 'release-PULSE.user-before-active-stop.toml'
assert not retained.exists()
retained.write_bytes(original)
probe = original + b'\n[[job]]\nname="daily-acceptance-stop-proposal"\nschedule="* * * * *"\ntype="script"\ncommand="hermes lifeos-job proposal-gc"\ntimeout_ms=600000\noutput="log"\nenabled=true\n'
services.drain(signature=services.preview()['signature'])
services.verify_stopped()
module('memory_transaction').publish(target, probe)
services.resume()
restored = False
try:
    group = subprocess.check_output(['systemctl', '--user', 'show', units['pulse'],
        '--property=ControlGroup', '--value'], text=True).strip()
    members_path = Path('/sys/fs/cgroup' + group) / 'cgroup.procs'
    deadline = time.monotonic() + 95
    active = []
    while time.monotonic() < deadline:
        active = []
        for value in members_path.read_text().splitlines():
            path = Path('/proc') / value
            try:
                args = (path / 'cmdline').read_bytes().split(b'\0')
                if b'lifeos-job' in args and b'proposal-gc' in args:
                    active.append({'pid': int(value), 'process': (path / 'comm').read_text().strip(),
                        'selected_job': 'proposal-gc'})
            except FileNotFoundError:
                continue
        if active:
            break
        time.sleep(0.1)
    assert active, 'The actual native scheduled owner job never starts'
    (stage / 'release-installed-active-job-start-observation.json').write_text(json.dumps({
        'control_group': group, 'active_owner_job_processes': active,
        'actual_job': 'hermes lifeos-job proposal-gc'}, indent=2) + '\n')
    started = time.monotonic()
    services.drain(signature=services.preview()['signature'])
    services.verify_stopped()
    elapsed = round(time.monotonic() - started, 3)
    assert elapsed < 45
    remaining = members_path.read_text().splitlines() if members_path.exists() else []
    assert not remaining
    module('memory_transaction').publish(target, original)
    restored = True
    services.resume()
    assert services.status()['state'] == 'active'
    assert target.read_bytes() == original
    report = {'status': 'PASS', 'observed_active_owner_job_processes': active,
        'drain_seconds': elapsed, 'acceptance_control_groups_verified_empty': True,
        'exact_daily_configuration_restored': True, 'service_state': services.status(),
        'synthetic_acceptance_profile_only': True, 'live_profile_changed': False,
        'private_model_inference_interruption_verified': False}
    (stage / 'release-installed-active-job-stop-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
finally:
    if not restored:
        services.quiesce()
        services.verify_stopped()
        module('memory_transaction').publish(target, original)
        services.resume()
