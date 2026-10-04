# ABOUTME: Reconstructs verified Hermes profile and native snapshots into separate owner recovery trees.
# ABOUTME: Rebinds candidate data links and configuration while keeping ownership and sharing disabled.
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .installation_lock import installation_lock
from .memory_access import MemoryUnavailable, NativeMemory
from .memory_backup import _directory, _read
from .memory_backup_recovery import recover as recover_native, _sync_tree
from .memory_preferences import MemoryPreferences
from .memory_transaction import publish
from .profile_backup import inspect


def _rebind_connector(stage, configuration, destination):
    connector = stage / 'native/.config/LIFEOS/USER/CONFIG/memory-access.json'
    if not connector.exists():
        return []
    data, metadata = _read(connector, private=True)
    try:
        document = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise MemoryUnavailable('The profile recovery has an invalid native connector') from error
    command = document.get('command') if isinstance(document, dict) else None
    profile = configuration.path.parent.absolute()
    if (not isinstance(document, dict) or type(document.get('version')) is not int or document['version'] != 1
            or not isinstance(command, list) or len(command) != 4
            or any(not isinstance(value, str) for value in command)
            or not Path(command[0]).is_absolute() or not Path(command[1]).is_absolute()
            or command[2] != '--configuration' or command[3] != str(configuration.path.absolute())):
        raise MemoryUnavailable('The profile recovery has an unsupported native connector')
    program = Path(command[1])
    if program.is_relative_to(profile) and program.name == 'memory_rpc.py':
        command[1] = str(destination / 'profile' / program.relative_to(profile))
    elif program != Path(__file__).with_name('memory_rpc.py').absolute():
        raise MemoryUnavailable('The profile recovery has an unreviewed native connector program')
    interpreter = Path(command[0])
    if interpreter.is_relative_to(profile):
        command[0] = str(destination / 'profile' / interpreter.relative_to(profile))
    command[3] = str(destination / 'profile' / configuration.path.name)
    publish(connector, (json.dumps(document, indent=2) + '\n').encode())
    connector.chmod(metadata['mode'])
    os.utime(connector, ns=(metadata['mtime_ns'], metadata['mtime_ns']))
    return [connector.relative_to(stage).as_posix()]


def recover(configuration, backup, signature, destination, *, account=None):
    if not isinstance(signature, str) or re.fullmatch('[0-9a-f]{64}', signature) is None:
        raise MemoryUnavailable('Profile recovery requires the reviewed backup signature')
    backup, destination = Path(backup).absolute(), Path(destination).absolute()
    with installation_lock(configuration.path.parent), configuration._lock():
        config = configuration.load()
        configuration.check_owner(config, account)
        manifest = inspect(configuration, backup, signature, account=account)
        profile = configuration.path.parent.absolute()
        memory = NativeMemory(Path(config['root']))
        user = (memory.root.parent / '.config/LIFEOS/USER').resolve()
        if any(destination.resolve().is_relative_to(path.resolve()) for path in (profile, memory.root, user, backup)):
            raise MemoryUnavailable('Profile recovery must remain outside live program, data, and backup trees')
        if destination.exists() or destination.is_symlink():
            raise MemoryUnavailable('An existing profile recovery tree cannot be replaced')
        if destination.parent.resolve() != destination.parent:
            raise MemoryUnavailable('The profile recovery destination changes its physical path')
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _directory(destination.parent)
        stage = Path(tempfile.mkdtemp(prefix='.profile-recovery-', dir=destination.parent))
        try:
            candidate = stage / 'profile'
            candidate.mkdir(mode=0o700)
            for item in sorted(manifest['directories'], key=lambda entry: len(Path(entry['path']).parts)):
                (candidate / item['path']).mkdir(parents=True, exist_ok=True, mode=0o700)
            for item in manifest['files']:
                data, _ = _read(backup / 'profile/files' / str(item['copy']), private=True)
                if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['digest']:
                    raise MemoryUnavailable('A profile recovery source changed after verification')
                if item['path'] == configuration.path.name:
                    rebound = json.loads(data)
                    configuration.validate(rebound)
                    rebound.update(root=str(destination / 'native/.claude'), ownership_enabled=False, sharing_enabled=False)
                    configuration.validate(rebound)
                    data = (json.dumps(rebound, indent=2) + '\n').encode()
                target = candidate / item['path']
                publish(target, data)
                target.chmod(item['mode'])
                os.utime(target, ns=(item['mtime_ns'], item['mtime_ns']))
            tools = (memory.root / 'LIFEOS/TOOLS').resolve()
            captured_tools = None
            if tools.is_relative_to(profile):
                relative = tools.relative_to(profile)
                if (relative / 'MemorySystem.ts').as_posix() in {item['path'] for item in manifest['files']}:
                    captured_tools = candidate / relative
            native = recover_native(memory, MemoryPreferences._owner_scope(config), backup / 'native',
                                    manifest['native_signature'], stage / 'native', program_tools=captured_tools)
            if captured_tools is not None:
                native['program_tools'] = str(destination / 'profile' / captured_tools.relative_to(candidate))
            for item in manifest['links']:
                original = Path(os.path.abspath(profile / Path(item['path']).parent / item['target']))
                if original.is_relative_to(user):
                    target = stage / 'native/.config/LIFEOS/USER' / original.relative_to(user)
                elif original.is_relative_to(profile):
                    target = candidate / original.relative_to(profile)
                else:
                    raise MemoryUnavailable('A profile recovery link has no candidate source')
                link = candidate / item['path']
                link.symlink_to(os.path.relpath(target, link.parent))
                os.utime(link, ns=(item['mtime_ns'], item['mtime_ns']), follow_symlinks=False)
            rebound_files = ['profile/' + configuration.path.name, *_rebind_connector(stage, configuration, destination)]
            inspect(configuration, backup, signature, account=account)
            for item in sorted(manifest['directories'], key=lambda entry: len(Path(entry['path']).parts), reverse=True):
                target = candidate / item['path']
                target.chmod(item['mode'])
                os.utime(target, ns=(item['mtime_ns'], item['mtime_ns']))
            native_receipt = stage / 'native/.native-recovery.json'
            native_metadata = json.loads(native_receipt.read_text())
            native_metadata['destination'] = str(destination / 'native')
            publish(native_receipt, (json.dumps(native_metadata, sort_keys=True, indent=2) + '\n').encode())
            receipt = {'version': 1, 'source_profile': str(profile), 'source_root': config['root'],
                       'principal': config['principal'], 'backup': str(backup), 'signature': signature,
                       'destination': str(destination), 'profile_files': len(manifest['files']),
                       'native_files': native['files'], 'active_facts': native['active_facts'],
                       'retired_facts': native['retired_facts'], 'ownership_enabled': False,
                       'sharing_enabled': False, 'program_tools': native['program_tools'], 'rebound_files': rebound_files}
            publish(stage / '.profile-recovery.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
            _sync_tree(stage)
            _directory(destination.parent)
            if destination.exists() or destination.is_symlink():
                raise MemoryUnavailable('An existing profile recovery tree cannot be replaced')
            os.rename(stage, destination)
            descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return {'status': 'recovered', 'profile': str(destination / 'profile'), 'root': str(destination / 'native/.claude'),
                    'signature': signature, 'profile_files': len(manifest['files']), 'native_files': native['files'],
                    'ownership_enabled': False, 'sharing_enabled': False, 'program_tools': native['program_tools'],
                    'recovery_manifest': str(destination / '.profile-recovery.json')}
        finally:
            if stage.exists():
                shutil.rmtree(stage)
