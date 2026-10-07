# ABOUTME: Applies the verified catalog callback fix to both existing .212 installations.
# ABOUTME: Journals a reversible code update while preserving profile and native data files.
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

REVISION = '02d7ac85d96fb416b3c8832928d274ec9ddab4cf'
OLD_MODEL = '6c23dc6c7fccf6dac0a28f863f223bfa3c567c67ac6cc5dcf975ed169046d55a'
NEW_MODEL = 'ca07054ca98d5bd2b28b9e45d2efacddea5e583330f4daa8efd4d327c31734dc'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_bytes(path, value, mode):
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.catalog-release')
    with temporary.open('wb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(mode)
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def save(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2) + '\n').encode(), 0o600)


def layout(target):
    if target == 'discord':
        home = Path('/home/lifeos-hermes')
        host = home / 'workspace/hermes-agent'
        units = ['hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service']
        uid, port, bun = 1004, 9119, home / '.bun/bin'
    else:
        home = Path('/home/lifeos-plugin-install-probe/acceptance-20261002')
        host = home / 'workspace/hermes'
        units = ['hermes-gateway.service', 'lifeos-acceptance-dashboard.service',
                 'lifeos-acceptance-native.service', 'lifeos-acceptance-pulse.service']
        uid, port, bun = 1007, 8921, home / '.local/bin'
    assert os.getuid() == uid
    profile = home / '.hermes'
    release = home / 'workspace/releases/20261004-catalog-02d7ac8'
    return {'target': target, 'home': home, 'host': host, 'profile': profile, 'release': release,
            'plugin': profile / 'plugins/lifeos-hook-bridge', 'native': (home / '.claude').resolve(),
            'units': units, 'uid': uid, 'port': port,
            'environment': {**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile),
                'PATH': str(bun) + ':' + os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1',
                'XDG_RUNTIME_DIR': f'/run/user/{uid}', 'DBUS_SESSION_BUS_ADDRESS': f'unix:path=/run/user/{uid}/bus'}}


def run(ctx, command, timeout=60):
    result = subprocess.run([str(item) for item in command], cwd=ctx['home'],
                            env=ctx['environment'], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        private = ctx['release'] / f'failure-{time.time_ns()}.txt'
        atomic_bytes(private, (result.stdout + result.stderr).encode(), 0o600)
        raise RuntimeError(f'{Path(command[0]).name} exits {result.returncode}; inspect {private.name}')
    return result.stdout


def services(ctx, action):
    return run(ctx, ['systemctl', '--user', action, *ctx['units']], timeout=60)


def stable_services(ctx):
    previous = None
    for _ in range(15):
        raw = run(ctx, ['systemctl', '--user', 'show', *ctx['units'], '-p', 'Id', '-p', 'ActiveState', '-p', 'MainPID'])
        rows = [dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
                for block in raw.strip().split('\n\n')]
        current = {row['Id']: int(row['MainPID']) for row in rows}
        if (len(rows) == len(ctx['units']) and all(row['ActiveState'] == 'active' for row in rows)
                and all(current.values()) and current == previous):
            return current
        previous = current
        time.sleep(2)
    raise RuntimeError('Services do not have stable active process IDs')


def protected(ctx):
    files = [ctx['profile'] / name for name in ['config.yaml', '.env', 'lifeos-memory.json', 'SOUL.md', 'USER.md']]
    files += [ctx['native'] / name for name in ['settings.json', 'CLAUDE.md']]
    return {str(path): sha(path) if path.is_file() else None for path in files}


def data_hashes(ctx):
    result = {}
    roots = [ctx['native'] / 'LIFEOS/USER', ctx['native'] / 'LIFEOS/MEMORY',
             ctx['profile'] / 'memories', ctx['profile'] / 'MEMORY.md']
    for root in roots:
        if not root.exists():
            continue
        paths = root.rglob('*') if root.is_dir() else [root]
        for path in paths:
            if path.is_file() and not path.is_symlink():
                result[str(path)] = sha(path)
    return result


def package_files(ctx):
    package = ctx['release'] / 'plugin-source/lifeos_hook_bridge'
    return {str(path.relative_to(package)): sha(path) for path in package.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}


def prepare(ctx):
    release = ctx['release']
    expected = package_files(ctx)
    changed = [name for name, digest in expected.items() if sha(ctx['plugin'] / name) != digest]
    assert changed == ['patches/hermes-plugin-events.patch'], changed
    assert sha(ctx['host'] / 'model_tools.py') == OLD_MODEL
    candidate = release / 'model_tools.candidate.py'
    assert sha(candidate) == NEW_MODEL
    compile(candidate.read_text(), str(candidate), 'exec')
    recorder = ctx['home'] / '.config/lifeos-development-capture/config.json'
    config = json.loads(recorder.read_text())
    assert config['enabled'] and all(sha(path) == digest for path, digest in config['fingerprints'].items())
    metadata = ctx['profile'] / 'plugins/.install-metadata.json'
    before_metadata = json.loads(metadata.read_text())['lifeos-hook-bridge']
    assert before_metadata['revision'] == 'd5dafbcac41434eb9aac2c4c7880a9b9be8135a4'
    files = [{'target': str(ctx['host'] / 'model_tools.py'), 'source': str(candidate), 'after': NEW_MODEL},
             {'target': str(ctx['plugin'] / changed[0]),
              'source': str(release / 'plugin-source/lifeos_hook_bridge' / changed[0]), 'after': expected[changed[0]]}]
    snapshot = release / 'snapshot'
    snapshot.mkdir(mode=0o700)
    for index, item in enumerate(files):
        path = Path(item['target'])
        item.update(before=sha(path), mode=path.stat().st_mode & 0o777)
        shutil.copy2(path, snapshot / f'code-{index}')
    shutil.copy2(recorder, snapshot / 'recorder-config.json')
    shutil.copy2(metadata, snapshot / 'install-metadata.json')
    save(release / 'preflight.json', {'revision': REVISION, 'files': files, 'package_files': expected,
         'protected': protected(ctx), 'recorder_path': str(recorder), 'metadata_path': str(metadata),
         'before_plugin_metadata': before_metadata, 'before_recorder_revision': config.get('plugin_revision')})
    print(json.dumps({'target': ctx['target'], 'prepared': True, 'runtime_files_changed': 2,
                      'plugin_files_verified': len(expected), 'dependency_changes': 0}))


def restore_files(ctx, state):
    for index, item in reversed(list(enumerate(state['files']))):
        path = Path(item['target'])
        assert sha(path) in {item['before'], item['after']}, 'Code changed after this release'
        before = ctx['release'] / 'snapshot' / f'code-{index}'
        assert sha(before) == item['before']
        atomic_bytes(path, before.read_bytes(), item['mode'])
    metadata = Path(state['metadata_path'])
    current = json.loads(metadata.read_text())
    assert current['lifeos-hook-bridge']['revision'] in {REVISION, state['before_plugin_metadata']['revision']}
    current['lifeos-hook-bridge'] = state['before_plugin_metadata']
    save(metadata, current)
    recorder = Path(state['recorder_path'])
    current = json.loads(recorder.read_text())
    assert current.get('plugin_revision') in {REVISION, state['before_recorder_revision']}
    current['plugin_revision'] = state['before_recorder_revision']
    save(recorder, current)


def check_sources(ctx, state):
    assert protected(ctx) == state['protected'], 'Protected profile changes'
    for item in state['files']:
        assert sha(item['target']) == item['after']
    assert all(sha(ctx['plugin'] / name) == digest for name, digest in state['package_files'].items())
    config = json.loads(Path(state['recorder_path']).read_text())
    assert config['plugin_revision'] == REVISION and config['enabled']
    assert all(sha(path) == digest for path, digest in config['fingerprints'].items())


def apply(ctx, state):
    release = ctx['release']
    assert protected(ctx) == state['protected']
    assert all(sha(item['target']) == item['before'] for item in state['files'])
    save(release / 'status.json', {'state': 'stopping', 'revision': REVISION})
    try:
        services(ctx, 'stop')
        before = data_hashes(ctx)
        save(release / 'data-before.json', before)
        assert protected(ctx) == state['protected']
        save(release / 'status.json', {'state': 'applying', 'revision': REVISION})
        for item in state['files']:
            source = Path(item['source'])
            assert sha(source) == item['after']
            atomic_bytes(item['target'], source.read_bytes(), item['mode'])
        metadata = Path(state['metadata_path'])
        current = json.loads(metadata.read_text())
        current['lifeos-hook-bridge'] = {**state['before_plugin_metadata'], 'revision': REVISION}
        save(metadata, current)
        recorder = Path(state['recorder_path'])
        current = json.loads(recorder.read_text())
        current['plugin_revision'] = REVISION
        save(recorder, current)
        assert data_hashes(ctx) == before, 'Code deployment changes user data'
        check_sources(ctx, state)
        services(ctx, 'start')
        pids = stable_services(ctx)
        interpreter = ctx['profile'] / 'tools/python-3.14.7+20260901-linux-x64/bin/python3'
        output = run(ctx, [interpreter, release / 'verify_catalog.py', ctx['host'], ctx['profile'], ctx['native'], release], timeout=120)
        catalog = json.loads(output)
        save(release / 'catalog-result.json', catalog)
        check_sources(ctx, state)
        save(release / 'status.json', {'state': 'verified', 'revision': REVISION, 'services': pids,
             'user_data_preserved_at_apply': True, 'profile_preserved': True, 'catalog': catalog})
        print(json.dumps({'target': ctx['target'], 'state': 'verified', 'revision': REVISION,
                          'services': pids, 'native_safety_context_delivered': True,
                          'user_data_preserved_at_apply': True, 'profile_preserved': True}))
    except BaseException:
        services(ctx, 'stop')
        restore_files(ctx, state)
        services(ctx, 'start')
        stable_services(ctx)
        save(release / 'status.json', {'state': 'rolled_back', 'revision': REVISION})
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', choices=['discord', 'acceptance'])
    parser.add_argument('action', choices=['prepare', 'apply', 'check', 'restore'])
    args = parser.parse_args()
    ctx = layout(args.target)
    spec = importlib.util.spec_from_file_location('catalog_installation_lock', ctx['plugin'] / 'installation_lock.py')
    lock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lock)
    with lock.installation_lock(ctx['profile']):
        if args.action == 'prepare':
            prepare(ctx)
        else:
            state = json.loads((ctx['release'] / 'preflight.json').read_text())
            if args.action == 'apply':
                apply(ctx, state)
            elif args.action == 'check':
                check_sources(ctx, state)
                print(json.dumps({'sources_verified': True, 'services': stable_services(ctx)}))
            else:
                before = data_hashes(ctx)
                services(ctx, 'stop')
                try:
                    restore_files(ctx, state)
                finally:
                    services(ctx, 'start')
                stable_services(ctx)
                assert data_hashes(ctx) == before
                save(ctx['release'] / 'status.json', {'state': 'restored', 'current_data_preserved': True})
                print('Prior code restored; current user data preserved.')


if __name__ == '__main__':
    main()
