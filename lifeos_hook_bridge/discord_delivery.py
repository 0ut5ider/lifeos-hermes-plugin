# ABOUTME: Admits private Discord writes against the current configured channel audience.
# ABOUTME: Binds each policy call to one Hermes profile without relying on a turn context.
from pathlib import Path

from .discord_audience import ChannelAudience, resolve_audience
from .memory_access import MemoryUnavailable
from .memory_service import MemoryConfiguration


class PrivateDiscordDelivery:
    def __init__(self, configuration, *, audience_lookup=None):
        self.configuration = MemoryConfiguration(configuration)
        self.audience_lookup = audience_lookup or resolve_audience

    def check(self, *, platform='', chat_id='', guild_id='', hermes_home='', **_):
        denied = {'action':'block','message':'Current Discord permissions do not admit private delivery'}
        try:
            if (platform != 'discord' or not isinstance(hermes_home,str)
                    or Path(hermes_home).absolute() != self.configuration.path.parent.absolute()):
                return denied
            configuration = self.configuration.load()
            binding = configuration.get('discord_channels',{}).get(chat_id)
            if binding is None or guild_id and guild_id != binding['guild']:
                return denied
            metadata = {'HERMES_SESSION_PLATFORM':'discord', 'HERMES_SESSION_CHAT_ID':chat_id,
                'HERMES_SESSION_CHAT_TYPE':'group', 'HERMES_SESSION_SCOPE_ID':binding['guild'],
                'HERMES_SESSION_USER_ID':binding['owner']}
            audience = self.audience_lookup(configuration,metadata)
            if (audience != ChannelAudience(chat_id,binding['owner'],configuration['principal'])
                    or self.configuration.load() != configuration):
                return denied
            return {'action':'allow'}
        except (MemoryUnavailable, ValueError, KeyError, OSError, TypeError, RuntimeError):
            return denied
