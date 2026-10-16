# ABOUTME: Serves authenticated HTTP memory tools with owner-selected client grants.
# ABOUTME: Keeps private credentials outside program releases and binds them to the selected installation.

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from urllib.parse import parse_qs, urlsplit

import anyio
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from .memory_access import MemoryUnavailable
from .memory_mcp import create_server
from .memory_service import MemoryConfiguration, MemoryService
from .memory_transaction import publish


HTTP_PREFIX = '/api/plugins/lifeos-hook-bridge/memory/http'
MCP_PATH = HTTP_PREFIX + '/mcp'
RESOURCE_METADATA_PATH = '/.well-known/oauth-protected-resource' + MCP_PATH
AUTH_METADATA_PATH = '/.well-known/oauth-authorization-server' + HTTP_PREFIX
SCOPE = 'lifeos:memory'
MAX_BODY = 1024 * 1024
MAX_CREDENTIAL_BYTES = 4 * 1024 * 1024


class CredentialUpdate:
    def __init__(self, store):
        self.store = store
        self.lock = store.lock._lock()
        self.value = None

    def __enter__(self):
        self.lock.__enter__()
        try:
            self.value = self.store.load()
            now = time.time()
            for field in ('tokens', 'requests', 'codes', 'clients'):
                self.value[field] = {key: item for key, item in self.value[field].items() if item['expires_at'] > now}
            return self.value
        except BaseException:
            self.lock.__exit__(None, None, None)
            raise

    def __exit__(self, error_type, error, traceback):
        try:
            if error_type is None:
                self.store.write(self.value)
        finally:
            # SDK OAuth errors are frozen exceptions. Passing them through a generator
            # context would make contextlib's traceback assignment replace the OAuth error.
            self.lock.__exit__(None, None, None)
        return False


def public_origin(value):
    if not isinstance(value, str) or len(value) > 2048 or value != value.strip():
        raise ValueError('Provide the HTTPS origin that serves this Hermes dashboard')
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError('Provide a valid public port') from error
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in ('', '/')
            or re.search(r'[\s\\"<>]', value)
            or parsed.scheme not in ('https', 'http')
            or (parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'))):
        raise ValueError('Use HTTPS, or HTTP on localhost, without a path, credentials, query, or fragment')
    authority = parsed.netloc.lower()
    if port == (443 if parsed.scheme == 'https' else 80):
        authority = '[' + parsed.hostname + ']' if ':' in parsed.hostname else parsed.hostname
    return f'{parsed.scheme}://{authority}'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class CredentialStore:
    def __init__(self, configuration):
        self.path = Path(configuration).with_name('lifeos-memory-http-credentials.json')
        self.lock = MemoryConfiguration(self.path)

    def load(self):
        try:
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        except FileNotFoundError:
            return {'version': 1, 'tokens': {}, 'clients': {}, 'requests': {}, 'codes': {}}
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise MemoryUnavailable('HTTP credentials require private owner files')
            data = stream.read(MAX_CREDENTIAL_BYTES + 1)
        if len(data) > MAX_CREDENTIAL_BYTES:
            raise MemoryUnavailable('HTTP credential storage exceeds its limit')
        value = json.loads(data)
        if value.get('version') != 1 or any(not isinstance(value.get(key), dict) for key in ('tokens', 'clients', 'requests', 'codes')):
            raise MemoryUnavailable('HTTP credentials are unavailable')
        return value

    def transaction(self):
        return CredentialUpdate(self)

    def write(self, value):
        data = (json.dumps(value, indent=2) + '\n').encode()
        if len(data) > MAX_CREDENTIAL_BYTES:
            raise MemoryUnavailable('HTTP credential storage exceeds its limit')
        if self.path.is_symlink():
            raise MemoryUnavailable('HTTP credentials must not be a symlink')
        if self.path.is_file() and self.path.read_bytes() == data:
            return
        publish(self.path, data)


class MemoryRemote:
    def __init__(self, configuration):
        self.configuration = MemoryConfiguration(configuration)
        self.store = CredentialStore(configuration)

    def _owner(self, config, account):
        if not isinstance(account, str) or not account.startswith('dashboard:'):
            raise PermissionError('An authenticated installation owner is required')
        self.configuration.check_owner(config, account)

    def binding(self, config):
        settings = config.get('http_mcp', {})
        return digest(json.dumps([str(self.configuration.path.absolute()), config['root'], config['principal'],
                                  settings.get('epoch'), settings.get('public_url')]))

    def current(self):
        config = self.configuration.load()
        settings = config.get('http_mcp', {})
        if (settings.get('enabled') is not True or config.get('ownership_enabled') is not True
                or not config.get('sharing_enabled')):
            raise MemoryUnavailable('HTTP memory sharing is disabled')
        if public_origin(settings['public_url']) != settings['public_url']:
            raise MemoryUnavailable('HTTP memory address is unavailable')
        return config

    def status(self, *, account):
        config = self.configuration.load()
        self._owner(config, account)
        settings = config.get('http_mcp', {})
        origin = settings.get('public_url', '')
        pending = []
        for identifier, item in self.store.load()['requests'].items():
            if item['expires_at'] > time.time() and item.get('binding') == self.binding(config):
                pending.append({'id': identifier, 'client_name': item['client_name'],
                                'redirect_uri': item['params']['redirect_uri'], 'expires_at': item['expires_at']})
        return {'enabled': settings.get('enabled', False), 'public_url': origin,
                'mcp_url': origin + MCP_PATH if origin else '', 'pending': pending,
                'sharing_enabled': config.get('sharing_enabled', False),
                'connections': [dict(client=key, **grant) for key, grant in config.get('clients', {}).items()
                                if grant.get('transport') == 'http']}

    def configure(self, request, *, account):
        if not isinstance(request, dict) or set(request) != {'enabled', 'public_url'} or type(request['enabled']) is not bool:
            raise ValueError('Provide the public HTTPS origin and whether HTTP MCP is enabled')
        origin = public_origin(request['public_url'])
        def change(config):
            self._owner(config, account)
            if request['enabled'] and config.get('ownership_enabled') is not True:
                raise ValueError('Activate LifeOS memory before enabling HTTP MCP')
            previous = config.get('http_mcp', {})
            epoch = previous.get('epoch')
            if previous.get('public_url') != origin or previous.get('enabled') != request['enabled']:
                epoch = secrets.token_hex(32)
                for grant in config.get('clients', {}).values():
                    if grant.get('transport') == 'http':
                        grant['enabled'] = False
            config['http_mcp'] = {'enabled': request['enabled'], 'public_url': origin, 'epoch': epoch}
        self.configuration.update(change)
        return self.status(account=account)

    @staticmethod
    def grant(request):
        required = {'client', 'read', 'write_project', 'projects', 'model_route'}
        if not isinstance(request, dict) or set(request) != required or type(request['write_project']) is not bool:
            raise ValueError('Provide a connection name, read categories, projects, declared model route, and project write choice')
        identifier = request['client']
        if not isinstance(identifier, str) or re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', identifier) is None:
            raise ValueError('Use a lowercase connection name with at most 64 letters, numbers, underscores, or hyphens')
        grant = {'enabled': True, 'transport': 'http', 'read': request['read'],
                 'write': ['project'] if request['write_project'] else [], 'projects': request['projects'],
                 'model_route': request['model_route']}
        MemoryConfiguration.validate({'version': 1, 'root': '/', 'principal': 'owner', 'clients': {identifier: grant}})
        if not grant['projects'] or len(grant['projects']) > 100 or len(grant['model_route']) > 256:
            raise ValueError('Select at least one project and a declared model route of at most 256 characters')
        return identifier, grant

    def _admit(self, request, account, prepare, *, expected_binding=None):
        identifier, grant = self.grant(request)
        with self.store.transaction() as value:
            with self.configuration._lock():
                config = self.configuration.load()
                self._owner(config, account)
                if expected_binding is not None and self.binding(config) != expected_binding:
                    raise MemoryUnavailable('The installation changes before approval')
                settings = config.get('http_mcp', {})
                if not settings.get('enabled') or not config.get('ownership_enabled'):
                    raise MemoryUnavailable('Enable HTTP memory before adding a connection')
                if identifier in config.get('clients', {}):
                    raise ValueError('This connection name already exists; use a distinct name')
                config.setdefault('clients', {})[identifier] = grant
                config['sharing_enabled'] = True
                self.configuration.validate(config)
                prepare(value, identifier, config)
                # A credential without a grant cannot authorize a request. Publication in
                # this order leaves policy unchanged when credential capacity or IO fails.
                self.store.write(value)
                self.configuration._publish(config)
        return identifier, config

    def enroll(self, request, *, account):
        token = secrets.token_urlsafe(32)
        def prepare(value, identifier, config):
            if len(value['tokens']) >= 1000:
                raise MemoryUnavailable('Revoke unused HTTP connections before adding another')
            value['tokens'][digest(token)] = {'kind': 'personal', 'grant': identifier,
                'binding': self.binding(config), 'expires_at': time.time() + 90 * 86400}
        identifier, config = self._admit(request, account, prepare)
        return {'client': identifier, 'token': token, 'mcp_url': config['http_mcp']['public_url'] + MCP_PATH,
                'expires_in': 90 * 86400, 'status': 'enrolled'}

    def authenticate(self, token):
        if not isinstance(token, str) or not 20 <= len(token) <= 512:
            return None
        try:
            config = self.current()
            entry = self.store.load()['tokens'].get(digest(token))
            if (not entry or entry['kind'] not in ('personal', 'access') or entry['expires_at'] <= time.time()
                    or entry['binding'] != self.binding(config)):
                return None
            MemoryService.client_scope(config, entry['grant'])
            return entry['grant']
        except (MemoryUnavailable, OSError, ValueError, KeyError):
            return None

    def revoke(self, identifier, *, account):
        def change(config):
            self._owner(config, account)
            grant = config.get('clients', {}).get(identifier)
            if not grant or grant.get('transport') != 'http':
                raise ValueError('This HTTP memory connection does not exist')
            grant['enabled'] = False
        self.configuration.update(change)
        with self.store.transaction() as value:
            for field in ('tokens', 'codes'):
                value[field] = {key: entry for key, entry in value[field].items() if entry.get('grant') != identifier}
        return {'status': 'revoked', 'client': identifier, 'records_deleted': False}

    def clear_unapproved(self, *, account):
        with self.store.transaction() as value:
            self._owner(self.configuration.load(), account)
            active = {entry['client_id'] for field in ('tokens', 'codes') for entry in value[field].values()
                      if entry.get('client_id') and entry.get('kind') != 'consumed_refresh'}
            removed = {key for key, entry in value['clients'].items() if not entry.get('approved') or key not in active}
            value['clients'] = {key: entry for key, entry in value['clients'].items() if key not in removed}
            requests = len(value['requests'])
            value['requests'] = {}
        return {'status': 'cleared', 'registrations_removed': len(removed), 'requests_removed': requests,
                'active_connections_preserved': True}


class MemoryRemoteMiddleware:
    def __init__(self, app, *, configuration, available=None):
        self.app = app
        self.remote = MemoryRemote(configuration)
        self.available = available

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] != 'http' or (path != MCP_PATH and path not in (RESOURCE_METADATA_PATH, AUTH_METADATA_PATH)
                and path not in {HTTP_PREFIX + '/' + name for name in ('authorize', 'token', 'register', 'revoke')}):
            return await self.app(scope, receive, send)

        async def private_send(message):
            if message['type'] == 'http.response.start':
                message = {**message, 'headers': [(key, value) for key, value in message.get('headers', [])
                    if key.lower() not in (b'cache-control', b'etag', b'last-modified')]
                    + [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]}
            await send(message)

        async def respond(status, body, headers=None):
            await JSONResponse(body, status_code=status, headers=headers)(scope, receive, private_send)

        try:
            config = self.remote.current()
            if self.available is not None and not self.available():
                raise MemoryUnavailable('The memory plugin is disabled')
        except (MemoryUnavailable, OSError, ValueError, KeyError):
            return await respond(404, {'error': 'HTTP memory sharing is unavailable'})
        origin = config['http_mcp']['public_url']
        request = Request(scope)
        if request.headers.get('host', '').lower() != urlsplit(origin).netloc:
            return await respond(421, {'error': 'Use the configured HTTP memory host'})
        try:
            peer = scope.get('client')
            loopback_proxy = bool(peer) and ipaddress.ip_address(peer[0]).is_loopback
        except ValueError:
            loopback_proxy = False
        if origin.startswith('http://') and not loopback_proxy:
            return await respond(400, {'error': 'Localhost HTTP requires a loopback connection'})
        if origin.startswith('https://') and scope.get('scheme') != 'https' and not loopback_proxy:
            return await respond(400, {'error': 'Use HTTPS or the local HTTPS proxy'})
        if request.headers.get('origin') not in (None, origin):
            return await respond(403, {'error': 'This request origin is not allowed'})
        if len(scope.get('query_string', b'')) > 8192:
            return await respond(414, {'error': 'The request URL exceeds its limit'})
        if scope.get('method') == 'POST':
            body = bytearray()
            try:
                with anyio.fail_after(15):
                    while True:
                        chunk = await receive()
                        if chunk['type'] != 'http.request':
                            return
                        body.extend(chunk.get('body', b''))
                        if len(body) > MAX_BODY:
                            return await respond(413, {'error': 'The request body exceeds its limit'})
                        if not chunk.get('more_body', False):
                            break
            except TimeoutError:
                return await respond(408, {'error': 'The request body times out'})
            if path == HTTP_PREFIX + '/token':
                try:
                    form = parse_qs(body.decode('utf-8'), max_num_fields=32)
                except (UnicodeError, ValueError):
                    return await respond(400, {'error': 'invalid_request'})
                if form.get('resource') != [origin + MCP_PATH]:
                    return await respond(400, {'error': 'invalid_target'})
            original_receive = receive
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await original_receive()
            receive = replay
        if path != MCP_PATH:
            from .memory_oauth import authorization_routes
            return await authorization_routes(self.remote, origin)(scope, receive, private_send)
        if scope.get('query_string'):
            return await respond(400, {'error': 'MCP credentials and identities must not appear in the URL'})
        authorization = request.headers.get('authorization', '')
        token = authorization[7:] if authorization.lower().startswith('bearer ') else ''
        client = await anyio.to_thread.run_sync(self.remote.authenticate, token)
        if not client:
            return await respond(401, {'error': 'invalid_token'}, {'WWW-Authenticate':
                f'Bearer resource_metadata="{origin + RESOURCE_METADATA_PATH}"'})
        def authorize():
            return (self.remote.authenticate(token) == client
                    and (self.available is None or self.available()))
        server = create_server(self.remote.configuration.path, client, authorize=authorize)
        manager = StreamableHTTPSessionManager(server, stateless=True, json_response=True,
            security_settings=TransportSecuritySettings(allowed_hosts=[urlsplit(origin).netloc], allowed_origins=[origin]),
            max_request_body_size=MAX_BODY)
        async with manager.run():
            await manager.handle_request(scope, receive, private_send)


def install_http_memory(app, configuration, *, available=None):
    if not getattr(app.state, 'lifeos_memory_http', False):
        app.add_middleware(MemoryRemoteMiddleware, configuration=configuration, available=available)
        app.state.lifeos_memory_http = True
