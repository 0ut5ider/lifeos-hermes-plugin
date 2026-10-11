# ABOUTME: Sends the governed daily morning brief to the fixed private Cerebo channel.
# ABOUTME: Binds generation and Hermes delivery to one current owner policy revision.
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from dotenv import dotenv_values

home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
sys.path[:0] = [str(profile / 'plugins'), str(home / 'runtime/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
configuration = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
selected = configuration.load()
assert selected['ownership_enabled'] and not selected['sharing_enabled']
channel = '1558870196784205927'
revision = module('memory_policy').MemoryPolicy(selected).revision
environment = dict(os.environ, HERMES_HOME=str(profile), LIFEOS_MEMORY_CONFIGURATION_REVISION=revision)
api = module('discord_audience').DiscordAPI(dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN'])
audience = module('discord_audience')
guard = module('discord_delivery').PrivateDiscordDelivery(configuration.path,
    audience_lookup=lambda c, metadata: audience.resolve_audience(c, metadata, api=api))
assert guard.check(platform='discord', chat_id=channel, hermes_home=str(profile))['action'] == 'allow'
result = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-job', 'life-morning-brief',
    '--configuration-revision', revision], env=environment, cwd=profile,
    capture_output=True, text=True, timeout=600)
assert result.returncode == 0 and not result.stderr, 'The governed morning brief refuses generation'
body = json.loads(result.stdout)
assert body['status'] == 'completed' and body['job'] == 'life-morning-brief'
output = body['output'].strip()
assert output and len(output.encode()) <= 65536, 'The morning brief has invalid output'
# Hermes interprets these markers as attachment instructions rather than narration.
if re.search(r'MEDIA:|\[\[(?:audio_as_voice|as_document)\]\]', output, re.IGNORECASE):
    raise ValueError('The text morning brief refuses transport directives')
configuration.check_revision(configuration.load(), revision)
assert guard.check(platform='discord', chat_id=channel, hermes_home=str(profile))['action'] == 'allow'
sent = subprocess.run([str(home / '.local/bin/hermes'), 'send', '--to', 'discord:' + channel,
    'LifeOS morning brief\n\n' + output], env=environment, cwd=profile,
    capture_output=True, text=True, timeout=120)
assert sent.returncode == 0, 'Hermes refuses current private morning-brief delivery'
print(json.dumps({'status': 'delivered', 'channel_id': channel, 'configuration_revision': revision}))
