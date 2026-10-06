# ABOUTME: Issues short-lived owner authorizations for native prompt mounting.
# ABOUTME: Binds detached work to private configuration and refuses conversation authority substitution.
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time

from .memory_access import MemoryUnavailable, NativeMemory
from .memory_policy import CATEGORIES, MemoryScope
from .memory_service import MemoryConfiguration
from .memory_transaction import publish


ENVIRONMENT = 'LIFEOS_MEMORY_ADMINISTRATION'
DIRECTORY = '.lifeos-memory-admin'
MAX_TTL = 3600


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def _directory(configuration, *, create=False):
    profile = configuration.path.parent.absolute()
    try:
        profile_info = profile.stat()
    except OSError as error:
        raise MemoryUnavailable('The administrative owner profile is unavailable') from error
    if profile.resolve() != profile or profile_info.st_uid != os.getuid() or profile_info.st_mode & 0o022:
        raise MemoryUnavailable('Administrative mounting needs the private owner profile')
    directory = profile / DIRECTORY
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
    try:
        info = directory.lstat()
    except OSError as error:
        raise MemoryUnavailable('Administrative authorization storage is unavailable') from error
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise MemoryUnavailable('Administrative authorization storage needs private owner permissions')
    return directory


def _read(path, limit):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > limit:
                raise MemoryUnavailable('Administrative authorization needs a private bounded owner file')
            content = stream.read(limit + 1)
            if len(content) > limit:
                raise MemoryUnavailable('Administrative authorization exceeds its size limit')
            return content
    except OSError as error:
        raise MemoryUnavailable('Administrative authorization is unavailable') from error


def _key(configuration, *, create=False):
    path = _directory(configuration, create=create) / 'key'
    if create:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(secrets.token_bytes(32))
                stream.flush()
                os.fsync(stream.fileno())
    key = _read(path, 32)
    if len(key) != 32:
        raise MemoryUnavailable('Administrative authorization key has an invalid size')
    return key


def required(installed, profile):
    connector = Path(installed) / 'LIFEOS/USER/CONFIG/memory-access.json'
    if connector.exists() or connector.is_symlink():
        return True
    configuration = Path(profile) / 'lifeos-memory.json'
    if not configuration.exists() and not configuration.is_symlink():
        return False
    if not (Path(installed) / 'LIFEOS').is_dir():
        # Without the installed tree, the connector state is unknown, as during update recovery.
        return True
    # An owner claim without enabled ownership keeps native memory standalone. Enabled
    # ownership stays managed when the connector is lost, and unreadable settings fail closed.
    try:
        return MemoryConfiguration(configuration).load().get('ownership_enabled', False) is not False
    except (ValueError, OSError, RuntimeError):
        return True


def _connector(configuration, config):
    root = Path(config['root']).absolute()
    NativeMemory(root)._boundary()
    connector = json.loads(_read(root / 'LIFEOS/USER/CONFIG/memory-access.json', 16384))
    command = connector.get('command') if isinstance(connector, dict) else None
    if (not isinstance(connector, dict) or connector.get('version') != 1
            or not isinstance(command, list) or len(command) != 4
            or any(not isinstance(value, str) for value in command)
            or not Path(command[0]).is_absolute() or not os.access(command[0], os.X_OK)
            or Path(command[1]).absolute() != Path(__file__).with_name('memory_rpc.py').absolute()
            or command[2] != '--configuration' or Path(command[3]).absolute() != configuration.path.absolute()):
        raise MemoryUnavailable('Administrative mounting requires the installed profile memory connector')


def issue(configuration, account, *, ttl=600, binding=None):
    if not isinstance(account, str) or not account.startswith('dashboard:'):
        raise PermissionError('An authenticated installation owner must authorize mounting')
    config = configuration.load()
    configuration.check_owner(config, account)
    if type(ttl) is not int or not 0 < ttl <= MAX_TTL or binding is not None and not isinstance(binding, dict):
        raise ValueError('Choose a bounded administrative authorization lifetime and job binding')
    purpose = 'recover' if binding is not None and binding.get('action') == 'recover' else 'mount'
    if purpose == 'mount':
        _connector(configuration, config)
    created = int(time.time())
    payload = {'version': 1, 'purpose': purpose, 'nonce': secrets.token_hex(16), 'account': account,
               'root': config['root'], 'profile': str(configuration.path.parent.absolute()),
               'configuration_digest': _digest(config), 'created': created, 'expires': created + ttl,
               'binding': binding}
    key = _key(configuration, create=True)
    document = {'payload': payload, 'signature': hmac.new(key, _encoded(payload), hashlib.sha256).hexdigest()}
    if len(_encoded(document)) > 8192:
        raise ValueError('Administrative authorization exceeds its size limit')
    path = _directory(configuration) / (payload['nonce'] + '.json')
    publish(path, _encoded(document))
    return path


def validate(configuration, authorization, *, binding=None, check_binding=False, purpose='mount'):
    if purpose not in ('mount', 'recover'):
        raise ValueError('Choose a mount or recovery authorization')
    path = Path(authorization).absolute()
    if path.parent != _directory(configuration) or re.fullmatch(r'[0-9a-f]{32}\.json', path.name) is None:
        raise PermissionError('This authorization belongs to another administrative profile')
    document = json.loads(_read(path, 8192))
    if (not isinstance(document, dict) or set(document) != {'payload', 'signature'}
            or not isinstance(document['signature'], str) or re.fullmatch('[0-9a-f]{64}', document['signature']) is None):
        raise PermissionError('Invalid administrative authorization')
    payload = document['payload']
    signature = hmac.new(_key(configuration), _encoded(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, document['signature']):
        raise PermissionError('Administrative authorization signature does not match')
    fields = {'version', 'purpose', 'nonce', 'account', 'root', 'profile', 'configuration_digest', 'created', 'expires', 'binding'}
    now = int(time.time())
    if (not isinstance(payload, dict) or set(payload) != fields or payload['version'] != 1
            or payload['purpose'] != purpose or not isinstance(payload['nonce'], str)
            or payload['nonce'] + '.json' != path.name or not isinstance(payload['account'], str)
            or not payload['account'].startswith('dashboard:')
            or type(payload['created']) is not int or type(payload['expires']) is not int
            or not payload['created'] <= now < payload['expires'] <= payload['created'] + MAX_TTL):
        raise PermissionError('Administrative authorization is invalid or expired')
    config = configuration.load()
    configuration.check_owner(config, payload['account'])
    if (payload['root'] != config['root'] or payload['profile'] != str(configuration.path.parent.absolute())
            or payload['configuration_digest'] != _digest(config)
            or check_binding and payload['binding'] != binding):
        raise PermissionError('Administrative configuration or job binding changed')
    categories = tuple(sorted(CATEGORIES)) if purpose == 'mount' else ()
    if purpose == 'mount':
        _connector(configuration, config)
    scope = MemoryScope(config['principal'], payload['account'], categories,
                        categories, ('*',) if categories else (), payload['configuration_digest'])
    return config, scope


def revoke(configuration, authorization):
    path = Path(authorization).absolute()
    if path.parent != _directory(configuration) or re.fullmatch(r'[0-9a-f]{32}\.json', path.name) is None:
        raise PermissionError('This authorization belongs to another administrative profile')
    path.unlink(missing_ok=True)


def mount_environment(installed, profile, authorization=None, *, binding=None):
    installed, profile = Path(installed).absolute(), Path(profile).absolute()
    environment = {key: value for key, value in os.environ.items()
                   if key not in (ENVIRONMENT, 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL')}
    environment.update(HOME=str(installed.parent), HERMES_HOME=str(profile))
    # A supplied grant is always validated, even while the connector is temporarily absent.
    configured = (profile / 'lifeos-memory.json').exists() or (profile / 'lifeos-memory.json').is_symlink()
    if required(installed, profile) or authorization is not None and configured:
        if authorization is None:
            raise PermissionError('Managed mounting requires installation owner authorization')
        configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
        purpose = 'recover' if binding is not None and binding.get('action') == 'recover' else 'mount'
        config, _ = validate(configuration, authorization, binding=binding, check_binding=True, purpose=purpose)
        if Path(config['root']).absolute() != installed:
            raise PermissionError('This authorization belongs to another LifeOS installation')
        if purpose == 'mount':
            environment[ENVIRONMENT] = str(Path(authorization).absolute())
    elif authorization is not None:
        raise PermissionError('Administrative authorization requires configured managed memory')
    return environment


def job_binding(job, request, action):
    return {'job': str(Path(job).absolute()), 'request_digest': _digest({key: value for key, value in request.items()
            if key != 'memory_authorization'}), 'action': action}


@contextmanager
def lease(configuration, account, **options):
    authorization = issue(configuration, account, **options)
    try:
        yield authorization
    finally:
        revoke(configuration, authorization)
