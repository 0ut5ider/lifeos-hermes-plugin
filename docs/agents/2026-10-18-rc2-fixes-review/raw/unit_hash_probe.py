# ABOUTME: Probes removal_recovery.dashboard_unit_environment against a real transient systemd unit.
# ABOUTME: Shows whether a password hash in Environment= survives parsing and authenticates.
import subprocess, sys, tempfile
from pathlib import Path
from ruamel.yaml import YAML
from plugins.dashboard_auth.basic import hash_password
from optional.lifeos_release_manager import inplace_services, removal_recovery
unit = 'rv2-hashprobe.service'
password = 'synthetic-probe-password'
encoded = hash_password(password)
subprocess.run(['systemd-run', '--user', '--unit=' + unit, '--collect',
                '-p', 'Environment=HERMES_DASHBOARD_BASIC_AUTH_USERNAME=probe-owner HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=' + encoded,
                'sleep', '60'], check=True, capture_output=True)
try:
    real_show = inplace_services.show
    inplace_services.show = lambda name, *props: real_show(unit, *props)
    assignments, files = removal_recovery.dashboard_unit_environment()
    print('parsed:', assignments)
    with tempfile.TemporaryDirectory() as folder:
        profile = Path(folder) / '.hermes'; profile.mkdir(mode=0o700)
        config = profile / 'config.yaml'
        with config.open('w') as stream: YAML().dump({'dashboard': {'basic_auth': {}}}, stream)
        config.chmod(0o600)
        settings = removal_recovery.basic_settings(profile)
        print('hash equal:', settings['password_hash'] == encoded)
        try:
            print('authenticate:', removal_recovery.authenticate(profile, 'probe-owner', password, 'dashboard:basic:probe-owner'))
        except Exception as error:
            print('authenticate refused:', type(error).__name__, error)
finally:
    subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True)
