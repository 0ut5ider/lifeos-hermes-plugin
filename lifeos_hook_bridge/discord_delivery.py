# ABOUTME: Admits private Discord writes against the current configured channel audience.
# ABOUTME: Binds each policy call to one Hermes profile without relying on a turn context.
from dataclasses import replace
from pathlib import Path

from .discord_audience import ChannelAudience, resolve_audience
from .memory_access import MemoryUnavailable
from .memory_service import MemoryConfiguration


class PrivateDiscordDelivery:
    def __init__(self, configuration, *, audience_lookup=None):
        self.configuration = MemoryConfiguration(configuration)
        self.audience_lookup = audience_lookup or resolve_audience

    def _mirror_admitted(self, configuration, chat_id, session_id):
        if not configuration.get('ownership_enabled', False):
            return True
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            return False
        from .memory_context import parse_context
        from .memory_runtime import MemoryRuntime
        runtime = MemoryRuntime(self.configuration.path)
        previous = runtime._states().get(session_id)
        if not isinstance(previous, dict) or not isinstance(previous.get('generation'), str):
            return False
        context = parse_context(previous.get('context'))
        binding = configuration.get('discord_channels', {}).get(chat_id)
        if (context.session_id != session_id or context.transport != 'discord'
                or configuration['accounts'].get('discord:' + context.author) != configuration['principal']
                or binding is not None and context.author != binding['owner']
                or context.destination != chat_id
                or context.visibility != 'private'
                or context.participants != (configuration['principal'],)):
            return False
        # Admission stamps omit the session from the scope signature. The stored
        # context above still binds this exact native session and destination.
        return runtime._scope(configuration, replace(context, session_id='')).signature == previous.get('scope')

    def check(self, *, platform='', chat_id='', guild_id='', hermes_home='',
              purpose='delivery', session_id='', **_):
        denied = {'action':'block','message':'Current Discord permissions do not admit private delivery'}
        try:
            if (platform != 'discord' or purpose not in ('delivery', 'mirror')
                    or not isinstance(hermes_home,str)
                    or Path(hermes_home).absolute() != self.configuration.path.parent.absolute()):
                return denied
            if (purpose == 'mirror' and not self.configuration.path.exists()
                    and not self.configuration.path.is_symlink()):
                return {'action': 'allow', 'mirror': True}
            configuration = self.configuration.load()
            if purpose == 'mirror' and not configuration.get('ownership_enabled', False):
                if self.configuration.load() != configuration:
                    return denied
                return {'action': 'allow', 'mirror': True}
            binding = configuration.get('discord_channels',{}).get(chat_id)
            if purpose == 'mirror' and binding is None:
                admitted = self._mirror_admitted(configuration, chat_id, session_id)
                if self.configuration.load() != configuration:
                    return denied
                return {'action': 'allow', 'mirror': admitted}
            if binding is None or guild_id and guild_id != binding['guild']:
                return denied
            metadata = {'HERMES_SESSION_PLATFORM':'discord', 'HERMES_SESSION_CHAT_ID':chat_id,
                'HERMES_SESSION_CHAT_TYPE':'group', 'HERMES_SESSION_SCOPE_ID':binding['guild'],
                'HERMES_SESSION_USER_ID':binding['owner']}
            audience = self.audience_lookup(configuration,metadata)
            if (audience != ChannelAudience(chat_id,binding['owner'],configuration['principal'])
                    or self.configuration.load() != configuration):
                return denied
            if purpose == 'mirror':
                admitted = self._mirror_admitted(configuration, chat_id, session_id)
                if self.configuration.load() != configuration:
                    return denied
                return {'action': 'allow', 'mirror': admitted}
            return {'action':'allow'}
        except (MemoryUnavailable, ValueError, KeyError, OSError, TypeError, RuntimeError):
            return denied
