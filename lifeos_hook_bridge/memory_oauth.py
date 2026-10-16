# ABOUTME: Issues OAuth memory credentials after authenticated installation owner consent.
# ABOUTME: Uses the MCP SDK for discovery, registration, PKCE validation, and token responses.

from __future__ import annotations

import secrets
import json
import time
from urllib.parse import urlsplit

from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizeError, RefreshToken,
    RegistrationError, TokenError, construct_redirect_uri,
)
from mcp.server.auth.routes import create_auth_routes, create_protected_resource_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.routing import Route, Router

from .memory_access import MemoryUnavailable
from .memory_service import MemoryService
from .memory_remote import AUTH_METADATA_PATH, HTTP_PREFIX, MCP_PATH, SCOPE, digest


UNAPPROVED_CLIENT_LIMIT = 128
APPROVED_CLIENT_LIMIT = 128
REGISTRATION_BYTES = 4096
OAUTH_TOKEN_LIMIT = 4096


class MemoryAuthorization:
    def __init__(self, remote):
        self.remote = remote

    async def get_client(self, client_id):
        entry = self.remote.store.load()['clients'].get(client_id)
        if entry and entry['expires_at'] > time.time():
            return OAuthClientInformationFull.model_validate(entry['metadata'])
        return None

    async def register_client(self, client_info):
        metadata = client_info.model_dump(mode='json')
        if len(json.dumps(metadata).encode()) > REGISTRATION_BYTES:
            raise RegistrationError('invalid_client_metadata', 'Registration metadata exceeds 4096 bytes')
        redirects = client_info.redirect_uris or []
        if not 1 <= len(redirects) <= 10 or len(client_info.client_name or '') > 256:
            raise RegistrationError('invalid_client_metadata', 'Provide a client name and at most ten redirect addresses')
        for redirect in redirects:
            address = urlsplit(str(redirect))
            if (len(str(redirect)) > 2048 or not address.hostname or address.fragment or address.username
                    or address.scheme not in ('https', 'http')
                    or (address.scheme == 'http' and address.hostname not in ('localhost', '127.0.0.1', '::1'))):
                raise RegistrationError('invalid_redirect_uri', 'Use an HTTPS redirect or a localhost HTTP callback')
        with self.remote.store.transaction() as value:
            if sum(not entry.get('approved') for entry in value['clients'].values()) >= UNAPPROVED_CLIENT_LIMIT:
                raise RegistrationError('invalid_client_metadata', 'The registration limit is reached')
            value['clients'][client_info.client_id] = {'metadata': metadata, 'approved': False,
                                                       'expires_at': time.time() + 600}

    async def authorize(self, client, params):
        config = self.remote.current()
        origin = config['http_mcp']['public_url']
        if (params.resource != origin + MCP_PATH or params.scopes != [SCOPE]
                or len(params.code_challenge) != 43 or len(params.state or '') > 2048):
            raise AuthorizeError('invalid_request', 'Use this MCP resource and the lifeos:memory scope with S256 PKCE')
        identifier = secrets.token_urlsafe(24)
        with self.remote.store.transaction() as value:
            if len(value['requests']) >= 100:
                raise AuthorizeError('temporarily_unavailable', 'The pending authorization limit is reached')
            value['requests'][identifier] = {'client_id': client.client_id,
                'client_name': client.client_name or 'Unnamed client', 'params': params.model_dump(mode='json'),
                'binding': self.remote.binding(config), 'expires_at': time.time() + 600}
        return origin + '/lifeos-bridge?memory_authorization=' + identifier

    def approve(self, identifier, request, *, account):
        config = self.remote.configuration.load()
        self.remote._owner(config, account)
        code = secrets.token_urlsafe(32)
        entry = None
        def prepare(value, grant, current):
            nonlocal entry
            entry = value['requests'].get(identifier)
            if not entry or entry['binding'] != self.remote.binding(current):
                raise ValueError('This authorization request expires or belongs to another installation')
            registered = value['clients'].get(entry['client_id'])
            if registered is None:
                raise ValueError('The unapproved client registration expires')
            if (not registered.get('approved') and sum(item.get('approved', False) for item in value['clients'].values()) >= APPROVED_CLIENT_LIMIT
                    or len(value['codes']) >= 100):
                raise MemoryUnavailable('Revoke unused OAuth connections before approving another')
            registered.update(approved=True, expires_at=time.time() + 365 * 86400)
            value['codes'][digest(code)] = {**entry, 'grant': grant, 'expires_at': time.time() + 120}
            del value['requests'][identifier]
        grant, current = self.remote._admit(request, account, prepare, expected_binding=self.remote.binding(config))
        params = entry['params']
        return {'status': 'approved', 'client': grant, 'redirect_url': construct_redirect_uri(
            params['redirect_uri'], code=code, state=params.get('state'),
            iss=current['http_mcp']['public_url'] + HTTP_PREFIX)}

    def deny(self, identifier, *, account):
        self.remote._owner(self.remote.configuration.load(), account)
        with self.remote.store.transaction() as value:
            entry = value['requests'].pop(identifier, None)
            if not entry:
                raise ValueError('This authorization request expires')
        return {'status': 'denied', 'redirect_url': construct_redirect_uri(
            entry['params']['redirect_uri'], error='access_denied', state=entry['params'].get('state'))}

    def _entry(self, field, token, kind=None):
        if not isinstance(token, str) or not 20 <= len(token) <= 512:
            return None
        try:
            config = self.remote.current()
            entry = self.remote.store.load()[field].get(digest(token))
            if (entry is None or entry['expires_at'] <= time.time() or entry['binding'] != self.remote.binding(config)
                    or (kind and entry['kind'] != kind)):
                return None
            MemoryService.client_scope(config, entry['grant'])
            return entry
        except (MemoryUnavailable, ValueError, OSError, KeyError):
            return None

    async def load_authorization_code(self, client, authorization_code):
        entry = self._entry('codes', authorization_code)
        if entry is None or entry['client_id'] != client.client_id:
            return None
        params = entry['params']
        return AuthorizationCode(code=authorization_code, client_id=client.client_id,
            scopes=params['scopes'], expires_at=entry['expires_at'], code_challenge=params['code_challenge'],
            redirect_uri=params['redirect_uri'], redirect_uri_provided_explicitly=params['redirect_uri_provided_explicitly'],
            resource=params['resource'], subject=entry['grant'])

    def _issue(self, value, entry):
        try:
            config = self.remote.current()
            if self.remote.binding(config) != entry['binding']:
                raise MemoryUnavailable('The selected installation changes')
            MemoryService.client_scope(config, entry['grant'])
        except (MemoryUnavailable, ValueError, OSError) as error:
            raise TokenError('invalid_grant', 'This memory connection is unavailable') from error
        family = entry.get('family', secrets.token_hex(24))
        value['tokens'] = {key: item for key, item in value['tokens'].items()
                           if item.get('family') != family or item['kind'] == 'consumed_refresh'}
        if len(value['tokens']) + 2 > OAUTH_TOKEN_LIMIT:
            raise TokenError('invalid_grant', 'Revoke unused OAuth connections before requesting more credentials')
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = int(time.time())
        common = {'client_id': entry['client_id'], 'grant': entry['grant'],
                  'binding': entry['binding'], 'family': family}
        value['tokens'][digest(access)] = {**common, 'kind': 'access', 'expires_at': now + 3600}
        value['tokens'][digest(refresh)] = {**common, 'kind': 'refresh', 'expires_at': now + 30 * 86400}
        return OAuthToken(access_token=access, refresh_token=refresh, token_type='Bearer', expires_in=3600, scope=SCOPE)

    async def exchange_authorization_code(self, client, authorization_code):
        with self.remote.store.transaction() as value:
            entry = value['codes'].pop(digest(authorization_code.code), None)
            if not entry or entry['client_id'] != client.client_id:
                raise TokenError('invalid_grant', 'This authorization code expires or is already used')
            return self._issue(value, entry)

    async def load_refresh_token(self, client, refresh_token):
        with self.remote.store.transaction() as value:
            entry = value['tokens'].get(digest(refresh_token))
            if entry and entry.get('kind') == 'consumed_refresh' and entry['client_id'] == client.client_id:
                self._revoke_family(value, entry['family'])
                return None
        entry = self._entry('tokens', refresh_token, 'refresh')
        if not entry or entry['client_id'] != client.client_id:
            return None
        return RefreshToken(token=refresh_token, client_id=client.client_id, scopes=[SCOPE],
                            expires_at=entry['expires_at'], subject=entry['grant'])

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        replay = False
        result = None
        with self.remote.store.transaction() as value:
            entry = value['tokens'].get(digest(refresh_token.token))
            if not entry or entry['client_id'] != client.client_id or scopes != [SCOPE]:
                raise TokenError('invalid_grant', 'This refresh credential expires or is already used')
            if entry['kind'] == 'consumed_refresh':
                self._revoke_family(value, entry['family'])
                replay = True
            elif entry['kind'] == 'refresh':
                value['tokens'][digest(refresh_token.token)] = {**entry, 'kind': 'consumed_refresh'}
                result = self._issue(value, entry)
            else:
                raise TokenError('invalid_grant', 'Use a current refresh credential')
        if replay:
            raise TokenError('invalid_grant', 'Refresh credential reuse revokes this connection family')
        return result

    @staticmethod
    def _revoke_family(value, family):
        value['tokens'] = {key: item for key, item in value['tokens'].items() if item.get('family') != family}

    async def load_access_token(self, token):
        entry = self._entry('tokens', token, 'access')
        if not entry:
            return None
        config = self.remote.current()
        return AccessToken(token=token, client_id=entry['client_id'], scopes=[SCOPE],
                           expires_at=entry['expires_at'], resource=config['http_mcp']['public_url'] + MCP_PATH,
                           subject=entry['grant'])

    async def revoke_token(self, token):
        with self.remote.store.transaction() as value:
            entry = value['tokens'].get(digest(token.token))
            if entry:
                self._revoke_family(value, entry['family'])


def authorization_routes(remote, origin):
    provider = MemoryAuthorization(remote)
    issuer = origin + HTTP_PREFIX
    routes = []
    for route in create_auth_routes(provider, issuer_url=AnyHttpUrl(issuer),
            client_registration_options=ClientRegistrationOptions(enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]),
            revocation_options=RevocationOptions(enabled=True)):
        path = AUTH_METADATA_PATH if route.path.startswith('/.well-known/') else HTTP_PREFIX + route.path
        routes.append(Route(path, endpoint=route.endpoint, methods=route.methods))
    routes.extend(create_protected_resource_routes(AnyHttpUrl(origin + MCP_PATH), [AnyHttpUrl(issuer)],
                  scopes_supported=[SCOPE], resource_name='LifeOS memory'))
    return Router(routes=routes)
