# ABOUTME: Verifies a configured Discord channel admits only its owner and selected bot.
# ABOUTME: Reads current channel, role, and membership permissions before private memory admission.
from dataclasses import dataclass
import json
import os
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


VIEW_CHANNEL = 1 << 10
ADMINISTRATOR = 1 << 3


def _identifier(value):
    return (isinstance(value, str) and len(value) <= 20 and value.isascii()
            and value.isdecimal() and 0 < int(value) < 2**64)


def validate_bindings(configuration):
    bindings = configuration.get('discord_channels', {})
    if not isinstance(bindings, dict):
        raise ValueError('Discord memory channels require fixed owner and bot bindings')
    for channel, binding in bindings.items():
        if (not _identifier(channel) or not isinstance(binding, dict)
                or set(binding) != {'guild', 'owner', 'bot'}
                or any(not _identifier(value) for value in binding.values())
                or binding['owner'] == binding['bot']):
            raise ValueError('Discord memory channels require numeric guild, owner, and bot identifiers')
        grant = configuration.get('destinations', {}).get('discord:' + channel, {})
        principal = configuration.get('principal')
        if (configuration.get('accounts', {}).get('discord:' + binding['owner']) != principal
                or grant.get('visibility') != 'private' or grant.get('participants') != [principal]):
            raise ValueError('Discord memory channels require the installation owner and a private destination grant')


@dataclass(frozen=True)
class ChannelAudience:
    channel: str
    owner: str
    principal: str


class _RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, location):
        raise ValueError('Discord audience requests cannot redirect bot credentials')


class DiscordAPI:
    def __init__(self, token, *, origin='https://discord.com/api/v10'):
        if not isinstance(token, str) or not token:
            raise ValueError('Discord audience verification requires the selected bot credential')
        self.token, self.origin = token, origin.rstrip('/')

    def get(self, path):
        request = Request(self.origin + path, headers={
            'Authorization': 'Bot ' + self.token,
            'User-Agent': 'LifeOS-Hermes/0.1.0'})
        with build_opener(_RefuseRedirects()).open(request, timeout=3) as response:
            data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('The Discord audience response exceeds its supported size')
        return json.loads(data)


def _permissions(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 20:
        raise ValueError('Discord audience permissions have invalid bits')
    bits = int(value)
    if bits >= 2**64:
        raise ValueError('Discord audience permissions exceed their supported bit range')
    return bits


def _bot_token():
    try:
        from agent.secret_scope import get_secret
    except ImportError:
        # Native workers receive the invoking profile's exported subprocess environment.
        return os.environ.get('DISCORD_BOT_TOKEN', '')
    return get_secret('DISCORD_BOT_TOKEN', '')


def _members(api, guild):
    members, seen, after = [], set(), ''
    for _ in range(10):
        page = api.get('/guilds/' + guild + '/members?limit=1000' + ('&after=' + after if after else ''))
        if not isinstance(page, list) or len(page) > 1000:
            raise ValueError('Discord audience membership is unavailable')
        for member in page:
            identifier = member['user']['id']
            if (not _identifier(identifier) or identifier in seen or not isinstance(member.get('roles'), list)
                    or any(not _identifier(role) for role in member['roles'])):
                raise ValueError('Discord audience membership has invalid identifiers')
            members.append(member); seen.add(identifier)
        if len(page) < 1000:
            return members
        after = page[-1]['user']['id']
    raise ValueError('Discord audience membership exceeds its supported review window')


def _readers(channel, guild, roles, members):
    role_bits = {}
    for role in roles:
        identifier = role['id']
        if not _identifier(identifier) or identifier in role_bits:
            raise ValueError('Discord audience roles have invalid identifiers')
        role_bits[identifier] = _permissions(role['permissions'])
    if guild['id'] not in role_bits:
        raise ValueError('Discord audience lacks its default role')
    overwrites = {}
    for item in channel['permission_overwrites']:
        identifier, kind = item['id'], item['type']
        if not _identifier(identifier) or type(kind) is not int or kind not in (0, 1) or (kind, identifier) in overwrites:
            raise ValueError('Discord audience channel permissions have invalid identifiers')
        overwrites[kind, identifier] = _permissions(item['deny']), _permissions(item['allow'])
    default = overwrites.get((0, guild['id']))
    if default is None or not default[0] & VIEW_CHANNEL or default[1] & VIEW_CHANNEL:
        raise ValueError('Discord personal memory requires an explicitly private channel')
    readers = set()
    for member in members:
        identifier = member['user']['id']
        bits = role_bits[guild['id']]
        for role in member['roles']:
            bits |= role_bits[role]
        if identifier == guild['owner_id'] or bits & ADMINISTRATOR:
            readers.add(identifier)
            continue
        bits = (bits & ~default[0]) | default[1]
        denied, allowed = 0, 0
        for role in member['roles']:
            deny, allow = overwrites.get((0, role), (0, 0))
            denied |= deny; allowed |= allow
        bits = (bits & ~denied) | allowed
        deny, allow = overwrites.get((1, identifier), (0, 0))
        bits = (bits & ~deny) | allow
        if bits & VIEW_CHANNEL:
            readers.add(identifier)
    return readers


def resolve_audience(configuration, metadata, *, api=None):
    try:
        validate_bindings(configuration)
        channel_id = metadata.get('HERMES_SESSION_CHAT_ID', '')
        binding = configuration.get('discord_channels', {}).get(channel_id)
        if (metadata.get('HERMES_SESSION_PLATFORM') != 'discord' or binding is None
                or metadata.get('HERMES_SESSION_CHAT_TYPE') != 'group'
                or metadata.get('HERMES_SESSION_THREAD_ID')
                or metadata.get('HERMES_CRON_SESSION') == '1'
                or metadata.get('HERMES_SESSION_SCOPE_ID') != binding['guild']
                or metadata.get('HERMES_SESSION_USER_ID') != binding['owner']):
            return None
        if api is None:
            api = DiscordAPI(_bot_token())
        bot = api.get('/users/@me')
        channel = api.get('/channels/' + channel_id)
        guild = api.get('/guilds/' + binding['guild'])
        roles = api.get('/guilds/' + binding['guild'] + '/roles')
        members = _members(api, binding['guild'])
        if (bot['id'] != binding['bot'] or bot.get('bot') is not True
                or channel['id'] != channel_id or channel['guild_id'] != binding['guild']
                or type(channel['type']) is not int or channel['type'] != 0
                or guild['id'] != binding['guild'] or guild['owner_id'] != binding['owner']
                or _readers(channel, guild, roles, members) != {binding['owner'], binding['bot']}):
            return None
        return ChannelAudience(channel_id, binding['owner'], configuration['principal'])
    except (ImportError, KeyError, TypeError, ValueError, OSError, URLError, RuntimeError):
        return None


def context_audience_is_current(configuration, context, *, audience_lookup=None):
    if context.transport != 'discord' or 'discord_channels' not in configuration:
        return True
    binding = configuration['discord_channels'].get(context.destination)
    if (binding is None or context.visibility != 'private'
            or context.participants != (configuration['principal'],)):
        return False
    metadata = {'HERMES_SESSION_PLATFORM':'discord', 'HERMES_SESSION_CHAT_ID':context.destination,
        'HERMES_SESSION_CHAT_TYPE':'group', 'HERMES_SESSION_SCOPE_ID':binding['guild'],
        'HERMES_SESSION_USER_ID':context.author, 'HERMES_SESSION_ID':context.session_id}
    audience = (audience_lookup or resolve_audience)(configuration, metadata)
    return audience == ChannelAudience(context.destination, context.author, configuration['principal'])
