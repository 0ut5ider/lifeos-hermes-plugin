# ABOUTME: Publishes a fresh native installation from private prepared program and user trees.
# ABOUTME: Resumes atomic publication without reading or replacing user data after publication.
import json
import os
from pathlib import Path
import re
import shutil
import stat
from uuid import uuid4

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_operation import request_digest
from .release_programs import fingerprint, publish, sync_directory


def native_identity(root, user):
    links = {'LIFEOS/USER': user, 'LIFEOS/MEMORY': user / 'MEMORY'}
    for name, target in links.items():
        path = root / name
        if not path.is_symlink() or os.readlink(path) != str(target):
            raise ReleaseRejected('The native installation changes its user-data links')
    return fingerprint(root, allow_links=True, external_links=links)


def private_directory(path):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or path.resolve() != path
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ReleaseRejected('Native initialization requires private physical owner storage')


class NativeInitialization:
    def __init__(self, job, request, installed):
        self.job, self.request, self.installed = job, request, installed
        self.user = installed.parent / '.config/LIFEOS/USER'
        self.seed = job / 'native-seed'
        self.journal = job / 'native-initialization.json'

    def record(self, value):
        publish(self.journal, (json.dumps(value, indent=2) + '\n').encode())

    def manifest(self):
        value = read_private(self.journal)
        if (set(value) != {'format', 'binding', 'installed', 'user', 'native_identity', 'user_identity', 'state'}
                or value['format'] != 1 or value['binding'] != request_digest(self.request)
                or value['installed'] != str(self.installed) or value['user'] != str(self.user)
                or value['state'] not in {'prepared', 'publishing-user', 'publishing-native', 'complete'}):
            raise ReleaseRejected('The native initialization changes its admitted destination')
        private_directory(self.seed)
        return value

    def prepare(self, helpers, *, checkpoint=lambda point: None):
        if self.journal.exists():
            return self.manifest()
        if (self.installed.exists() or self.installed.is_symlink()
                or self.user.exists() or self.user.is_symlink()):
            raise ReleaseRejected('A fresh destination gains existing data before installation')
        principal, assistant = helpers._name(self.request['name']), helpers._name(self.request['assistant'])
        if self.seed.exists() or self.seed.is_symlink():
            private_directory(self.seed)
            self.seed.rename(self.job / ('native-seed-incomplete-' + uuid4().hex))
            sync_directory(self.job)
        self.seed.mkdir(mode=0o700)
        reference = Path(self.request['runtime']['reference'])
        source_user = (reference / 'LIFEOS/USER').resolve(strict=True)
        user, native = self.seed / 'user', self.seed / 'native'
        shutil.copytree(source_user, user)
        user.chmod(0o700)
        helpers._empty_personal_templates(user, self.job / 'fresh-templates')
        for name in helpers.IDENTITY_FILES:
            path = user / name
            data = path.read_bytes()
            helpers.publish(self.job / 'fresh-templates/identity-originals' / name, data)
            if name == 'CONFIG/LIFEOS_CONFIG.toml':
                rendered = helpers._config_names(data, principal, assistant)
            elif name.startswith('PRINCIPAL/'):
                rendered = re.sub(r'\bUser\b', lambda _: principal, data.decode()).encode()
            else:
                text = data.decode().replace('LifeOS Assistant', assistant).replace('LifeOS', assistant)
                rendered = re.sub(r'\bUser\b', lambda _: principal, text).encode()
            publish(path, rendered)
        shutil.copytree(reference, native, symlinks=True)
        link = native / 'LIFEOS/USER'
        if not link.is_symlink():
            raise ReleaseRejected('The native reference has no expected user-data link')
        link.unlink()
        link.symlink_to(self.user, target_is_directory=True)
        memory = native / 'LIFEOS/MEMORY'
        if memory.is_symlink() or not memory.is_dir() or (user / 'MEMORY').exists():
            raise ReleaseRejected('The fresh native memory scaffold changes its expected layout')
        memory.rename(user / 'MEMORY')
        memory.symlink_to(self.user / 'MEMORY', target_is_directory=True)
        settings = native / 'settings.json'
        publish(settings, settings.read_bytes().replace(str(reference.parent).encode(), str(self.installed.parent).encode()))
        value = {'format': 1, 'binding': request_digest(self.request), 'installed': str(self.installed),
                 'user': str(self.user), 'native_identity': native_identity(native, self.user),
                 'user_identity': fingerprint(user), 'state': 'prepared'}
        self.record(value)
        checkpoint('seed-prepared')
        return value

    def execute(self, helpers, *, checkpoint=lambda point: None):
        value = self.prepare(helpers, checkpoint=checkpoint)
        native, user = self.seed / 'native', self.seed / 'user'
        if native.exists() and native_identity(native, self.user) != value['native_identity']:
            raise ReleaseRejected('The prepared native programs change before publication')
        if self.installed.exists():
            if native.exists() or native_identity(self.installed, self.user) != value['native_identity']:
                raise ReleaseRejected('Native recovery preserves a later program edit')
        elif self.installed.is_symlink() or not native.exists():
            raise ReleaseRejected('The prepared native programs are unavailable')
        if self.installed.parent.resolve() != self.installed.parent or self.user.parent.resolve() != self.user.parent:
            raise ReleaseRejected('Native initialization changes its physical destination')
        self.user.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if user.exists():
            if fingerprint(user) != value['user_identity']:
                raise ReleaseRejected('The prepared user scaffold changes before publication')
            if self.user.exists() or self.user.is_symlink() or value['state'] not in {'prepared', 'publishing-user'}:
                raise ReleaseRejected('Native recovery preserves an existing user destination')
            value['state'] = 'publishing-user'
            self.record(value)
            checkpoint('user-publication-intent')
            user.rename(self.user)
            sync_directory(self.user.parent)
            sync_directory(self.seed)
        else:
            if value['state'] == 'prepared':
                raise ReleaseRejected('The prepared user scaffold is unavailable')
            private_directory(self.user)
        checkpoint('user-published')
        if native.exists():
            value['state'] = 'publishing-native'
            self.record(value)
            checkpoint('native-publication-intent')
            native.rename(self.installed)
            sync_directory(self.installed.parent)
            sync_directory(self.seed)
        checkpoint('native-published')
        value['state'] = 'complete'
        self.record(value)
        return {'state': 'complete'}
