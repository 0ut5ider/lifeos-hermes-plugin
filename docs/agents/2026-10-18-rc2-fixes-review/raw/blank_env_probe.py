# ABOUTME: Compares LifeOS basic_settings with Hermes's own env loading when the profile .env blanks a unit value.
# ABOUTME: Runs Hermes load_hermes_dotenv over a simulated unit environment and reads the plugin _settings.
import os, sys, tempfile
from pathlib import Path
from ruamel.yaml import YAML
from plugins.dashboard_auth.basic import hash_password
from optional.lifeos_release_manager.removal_recovery import basic_settings
folder = tempfile.mkdtemp(); profile = Path(folder) / '.hermes'; profile.mkdir(mode=0o700)
config = profile / 'config.yaml'
with config.open('w') as stream:
    YAML().dump({'dashboard': {'basic_auth': {'username': 'owner', 'password_hash': hash_password('config-password')}}}, stream)
config.chmod(0o600)
env = profile / '.env'; env.write_text('HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=\n'); env.chmod(0o600)
unit = (['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=unit-password'], [])
lifeos = basic_settings(profile, unit=lambda: unit)
from plugins.dashboard_auth.basic import _verify_password
print('LifeOS accepts unit-password:', _verify_password('unit-password', lifeos['password_hash']))
print('LifeOS accepts config-password:', _verify_password('config-password', lifeos['password_hash']))
os.environ['HERMES_HOME'] = str(profile); os.environ['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD'] = 'unit-password'
from hermes_cli.env_loader import load_hermes_dotenv
load_hermes_dotenv(hermes_home=profile)
print('Hermes env value after .env load:', repr(os.environ.get('HERMES_DASHBOARD_BASIC_AUTH_PASSWORD')))
