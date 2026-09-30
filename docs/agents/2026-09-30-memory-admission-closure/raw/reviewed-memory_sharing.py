# ABOUTME: Enrolls restricted SSH keys with fixed server-owned memory client grants.
# ABOUTME: Revokes interface access before removing a key and preserves unrelated SSH entries.
from __future__ import annotations

import base64
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
from typing import Any

from .memory_service import MemoryConfiguration
from .memory_transaction import publish


def validate_public_key(value: str) -> str:
    if not isinstance(value, str) or len(value) > 1024:
        raise ValueError('Provide one OpenSSH Ed25519 public key')
    value = value.strip()
    if '\n' in value or '\r' in value:
        raise ValueError('Provide one OpenSSH Ed25519 public key')
    fields = value.split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519':
        raise ValueError('Provide an OpenSSH Ed25519 public key without key options')
    try:
        raw = base64.b64decode(fields[1], validate=True)
        cursor = 0
        pieces = []
        for _ in range(2):
            length = struct.unpack_from('>I', raw, cursor)[0]; cursor += 4
            pieces.append(raw[cursor:cursor+length]); cursor += length
        if cursor != len(raw) or pieces[0] != b'ssh-ed25519' or len(pieces[1]) != 32:
            raise ValueError('Invalid key structure')
    except (ValueError, struct.error) as error:
        raise ValueError('Invalid Ed25519 public key') from error
    return 'ssh-ed25519 ' + fields[1]


def key_fingerprint(key: str) -> str:
    digest = hashlib.sha256(base64.b64decode(key.split()[1], validate=True)).digest()
    return 'SHA256:' + base64.b64encode(digest).decode().rstrip('=')


def enrolled_line(line: str, identifier: str, fingerprint: str) -> bool:
    if not line.startswith('restrict,command='):
        return False
    try:
        fields = shlex.split(line)
        if len(fields) != 4 or fields[1] != 'ssh-ed25519' or fields[3] != 'lifeos-memory:' + identifier:
            return False
        return key_fingerprint(validate_public_key(' '.join(fields[1:3]))) == fingerprint
    except ValueError:
        return False


class MemorySharing:
    def __init__(self, configuration: Path, authorized_keys: Path, interpreter: Path, program: Path):
        self.configuration = MemoryConfiguration(configuration)
        self.authorized_keys = authorized_keys
        self.interpreter, self.program = interpreter, program
        if any(not path.is_absolute() for path in (configuration, authorized_keys, interpreter, program)):
            raise ValueError('Memory connection paths must be absolute')

    def _keys(self) -> str:
        parent = self.authorized_keys.parent
        info = parent.stat()
        if parent.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('SSH key directory needs private owner permissions')
        if self.authorized_keys.is_symlink():
            raise ValueError('SSH keys file must not be a symlink')
        if not self.authorized_keys.exists():
            return ''
        info = self.authorized_keys.stat()
        if not self.authorized_keys.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('SSH keys file needs private owner permissions')
        return self.authorized_keys.read_text()

    @contextmanager
    def _lock(self):
        self._keys()
        path = self.authorized_keys.parent / 'lifeos-memory-enrollment.lock'
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('SSH enrollment lock needs private owner permissions')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _key_line(self, identifier: str, key: str) -> str:
        home = self.authorized_keys.parent.parent
        bun = shutil.which('bun')
        if not bun or not Path(bun).is_absolute():
            raise ValueError('Install Bun before enrolling a memory connection')
        tools = str(Path(bun).parent) + ':/usr/bin:/bin'
        command = ('/usr/bin/env -i PATH=' + shlex.quote(tools) + ' HOME=' + shlex.quote(str(home))
                   + ' SSH_ORIGINAL_COMMAND="$SSH_ORIGINAL_COMMAND" '
                   + ' '.join(shlex.quote(str(arg)) for arg in (self.interpreter, '-I', self.program,
                        '--configuration', self.configuration.path, '--client', identifier, '--ssh')))
        escaped = command.replace('\\', '\\\\').replace('"', '\\"')
        return f'restrict,command="{escaped}" {key} lifeos-memory:{identifier}\n'

    def enroll(self, identifier: str, public_key: str, *, projects: list[str], model_route: str,
               read: list[str] | None = None, write_project: bool = False) -> dict[str, Any]:
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', identifier):
            raise ValueError('Use a new connection name with letters, digits, underscores, or hyphens')
        if type(write_project) is not bool:
            raise ValueError('Project write access needs an explicit boolean choice')
        key = validate_public_key(public_key)
        if not self.program.is_file() or not os.access(self.interpreter, os.X_OK):
            raise ValueError('The installed memory process and interpreter must be available')
        with self._lock():
            previous = self._keys()
            if key.split()[1] in previous.split():
                raise ValueError('This public key already has an SSH entry; use a separate key for memory')
            line = self._key_line(identifier, key)
            grant = {'enabled': True, 'read': ['project'] if read is None else read,
                     'write': ['project'] if write_project else [], 'projects': projects, 'model_route': model_route,
                     'credential_fingerprint': key_fingerprint(key)}
            def activate(config):
                if identifier in config.get('clients', {}):
                    raise ValueError('This connection name already exists; use a new name after revocation')
                config.setdefault('clients', {})[identifier] = grant
                config['sharing_enabled'] = True
            self.configuration.update(activate)
            try:
                publish(self.authorized_keys, (previous + ('' if not previous or previous.endswith('\n') else '\n')
                                              + line).encode())
            except BaseException:
                self.configuration.update(lambda config: config['clients'][identifier].update(enabled=False))
                raise
        return {'status': 'enrolled', 'client': identifier, 'permissions': grant,
                'transport': 'SSH process', 'command': 'lifeos-memory'}

    def revoke(self, identifier: str) -> dict[str, Any]:
        with self._lock():
            previous = self._keys()
            def disable(config):
                grant = config.get('clients', {}).get(identifier)
                if grant is None:
                    raise ValueError('This memory connection does not exist')
                grant['enabled'] = False
            config = self.configuration.update(disable)
            fingerprint = config['clients'][identifier].get('credential_fingerprint', '')
            kept = [line for line in previous.splitlines(keepends=True)
                    if not enrolled_line(line, identifier, fingerprint)]
            publish(self.authorized_keys, ''.join(kept).encode())
        return {'status': 'revoked', 'client': identifier, 'records_deleted': False}
