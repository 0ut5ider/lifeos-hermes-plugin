# ABOUTME: Applies the reviewed external recorder with private rollback backups.
# ABOUTME: Restarts the two development services and verifies native source identity.

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

home = Path.home()
workspace = home / 'workspace/development-hook-capture'
source = workspace / 'development'
staged = workspace / '.staging-review-fixes/development'
config_path = home / '.config/lifeos-development-capture/config.json'
config = json.loads(config_path.read_text())
site = home / '.hermes/tools/python-3.14.7+20260901-linux-x64/lib/python3.14/site-packages'
stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
backup_source = workspace / ('development.before-reviewed-' + stamp)
backup_config = config_path.with_name('config.json.before-reviewed-' + stamp)
unit_names = ['hermes-gateway.service', 'hermes-dashboard.service']
environment = dict(os.environ, XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
                   DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')


def service(*arguments, check=True):
    return subprocess.run(['systemctl', '--user', *arguments], env=environment,
                          capture_output=True, text=True, check=check)


def fingerprints():
    return {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in config['fingerprints']}


before = fingerprints()
assert before == config['fingerprints'], 'Native source drift requires inspection'
assert staged.is_dir() and source.is_dir(), 'Missing recorder staging source'
assert not backup_source.exists() and not backup_config.exists(), 'Backup already exists'
shutil.copyfile(config_path, backup_config)
backup_config.chmod(0o600)
changed = False
try:
    service('stop', *unit_names)
    source.rename(backup_source)
    changed = True
    staged.rename(source)
    spec = importlib.util.spec_from_file_location('reviewed_capture_setup', source / 'hook_capture/setup.py')
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    installed = setup.install(config['plugin_root'], config['host_root'], config['root'], config_path, site)
    updated = json.loads(config_path.read_text())
    assert fingerprints() == before, 'Native sources changed'
    service('start', *unit_names)
    previous_pids = {}
    stable_checks = 0
    for attempt in range(30):
        pids = {unit: int(service('show', unit, '-p', 'MainPID', '--value').stdout.strip()) for unit in unit_names}
        active = all(service('is-active', unit, check=False).stdout.strip() == 'active' for unit in unit_names)
        stable_checks = stable_checks + 1 if active and all(pids.values()) and pids == previous_pids else 0
        if stable_checks >= 3:
            break
        previous_pids = pids
        time.sleep(1)
    else:
        raise RuntimeError('Services do not become active')
    print(json.dumps({'applied': True, 'native_sources_unchanged': before == fingerprints(),
                     'backup_source': str(backup_source), 'backup_config': str(backup_config),
                     'services': pids, 'capture_sources': updated['capture_sources'], 'installation': installed}))
except Exception:
    if changed:
        service('stop', *unit_names, check=False)
        if source.exists():
            source.rename(workspace / ('development.failed-reviewed-' + stamp))
        backup_source.rename(source)
        shutil.copyfile(backup_config, config_path)
        config_path.chmod(0o600)
    service('start', *unit_names, check=False)
    raise
