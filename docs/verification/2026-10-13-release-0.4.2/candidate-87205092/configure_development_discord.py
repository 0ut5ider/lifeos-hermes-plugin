# ABOUTME: Grants the authenticated owner a verified private development Discord destination.
# ABOUTME: Preserves private model selection and records reversible channel configuration changes.
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

from dotenv import dotenv_values, set_key
from ruamel.yaml import YAML

os.umask(0o077)
sys.dont_write_bytecode = True
profile = Path.home() / '.hermes'
stage = Path.home() / 'releases/qualification-0.4.2-87205092'
sys.path[:0] = [str(profile / 'plugins'), str(profile / '.lifeos-releases/3240c42939f2451293bd9d5cfcd8bf12/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
proof = json.loads((stage / 'development-owner-authority.json').read_bytes())
assert proof['http_status'] == 200
assert proof['session']['provider'] == 'basic' and proof['session']['user_id'] == 'release-owner'
assert proof['session']['expires_at'] > time.time()
account = 'dashboard:basic:release-owner'
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
selected = configuration.load()
configuration.check_owner(selected, account)
assert selected['ownership_enabled'] is True and selected['sharing_enabled'] is False
model = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())['model']
route = module('memory_context').route_identity(model.get('provider', 'custom'), model['default'],
    model['base_url'], model.get('api_mode', 'chat_completions'))
channel, owner, guild, bot = '1559717651817697361', '708089927468056648', '1553540018302099486', '1554102173535703140'
values = dotenv_values(profile / '.env')
assert values['DISCORD_ALLOWED_USERS'] == owner
audience = module('discord_audience')
api = audience.DiscordAPI(values['DISCORD_BOT_TOKEN'])
metadata = {'HERMES_SESSION_PLATFORM': 'discord', 'HERMES_SESSION_CHAT_ID': channel,
    'HERMES_SESSION_CHAT_TYPE': 'group', 'HERMES_SESSION_SCOPE_ID': guild, 'HERMES_SESSION_USER_ID': owner}


def grant(value):
    configuration.check_owner(value, account)
    assert value == selected
    value['accounts']['discord:' + owner] = value['principal']
    value.setdefault('discord_channels', {})[channel] = {'guild': guild, 'owner': owner, 'bot': bot}
    value['destinations']['discord:' + channel] = {'visibility': 'private', 'participants': [value['principal']],
        'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
        'projects': ['*'], 'model_routes': [route]}
    assert audience.resolve_audience(value, metadata, api=api) == audience.ChannelAudience(channel, owner, value['principal'])


draft = copy.deepcopy(selected)
grant(draft)
before = hashlib.sha256((profile / 'config.yaml').read_bytes()).hexdigest()
backup = stage / 'environment-before-private-development.env'
assert not backup.exists()
backup.write_bytes((profile / '.env').read_bytes())
backup.chmod(0o600)
configuration_backup = stage / 'memory-policy-before-private-development.json'
configuration_backup.write_bytes(configuration.path.read_bytes())
configuration_backup.chmod(0o600)
configuration.update(grant)
keys = ('DISCORD_ALLOWED_CHANNELS', 'DISCORD_FREE_RESPONSE_CHANNELS', 'DISCORD_HOME_CHANNEL')
for key in keys:
    set_key(profile / '.env', key, channel)
assert hashlib.sha256((profile / 'config.yaml').read_bytes()).hexdigest() == before
assert audience.resolve_audience(configuration.load(), metadata, api=api) is not None
report = {'status': 'PASS', 'channel': channel, 'channel_name': 'hermes-dev', 'bot': bot,
    'private_audience_verified': True, 'readers': [owner, bot],
    'previous_channel_configuration': {key: values.get(key) for key in keys},
    'model_configuration_sha256': before, 'model_routes_changed': False,
    'daily_server_changed': False, 'credentials_exported': False,
    'undo': 'Restore the two private configuration backups and restart the development gateway. The created channel can then be removed.'}
(stage / 'development-private-discord-configuration.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
