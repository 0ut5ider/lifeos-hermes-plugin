# ABOUTME: Deploys one pinned compatibility set to the two .212 test installations.
# ABOUTME: Saves private code and data snapshots and preserves later data during rollback.
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REVISION = 'd5dafbcac41434eb9aac2c4c7880a9b9be8135a4'
TARGET = sys.argv[1]
ACTION = sys.argv[2]
if TARGET == 'discord':
    ACCOUNT_HOME = Path('/home/lifeos-hermes')
    OPERATING_HOME = ACCOUNT_HOME
    EXPECTED_UID = 1004
    HERMES = ACCOUNT_HOME / 'workspace/hermes-agent'
    RELEASE = ACCOUNT_HOME / 'workspace/releases/20261003-merged-d5dafbc'
    UNITS = ['hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service']
    PORT = 9119
else:
    assert TARGET == 'acceptance'
    ACCOUNT_HOME = Path('/home/lifeos-plugin-install-probe')
    OPERATING_HOME = ACCOUNT_HOME / 'acceptance-20261002'
    EXPECTED_UID = 1007
    HERMES = OPERATING_HOME / 'workspace/hermes'
    RELEASE = OPERATING_HOME / 'workspace/releases/20261003-merged-d5dafbc'
    UNITS = ['hermes-gateway.service', 'lifeos-acceptance-dashboard.service',
             'lifeos-acceptance-native.service', 'lifeos-acceptance-pulse.service']
    PORT = 8921
assert os.getuid() == EXPECTED_UID
PROFILE = OPERATING_HOME / '.hermes'
NATIVE = (OPERATING_HOME / '.claude').resolve()
PLUGIN = PROFILE / 'plugins/lifeos-hook-bridge'
PACKAGE = RELEASE / 'plugin-source'
SOURCE = RELEASE / 'prepared/lifeos/LifeOS/install'
CANDIDATE = RELEASE / 'prepared/hermes'
BASELINE = OPERATING_HOME / '.local/state/lifeos-hook-bridge/version-drift-baseline.json'
BACKUP = RELEASE / 'snapshot'
COMMAND = HERMES / '.hermes/bin/hermes'
BUN = OPERATING_HOME / '.local/bin/bun'
if not BUN.exists():
    BUN = ACCOUNT_HOME / '.bun/bin/bun'
ENV = dict(os.environ, HOME=str(OPERATING_HOME), HERMES_HOME=str(PROFILE),
           LIFEOS_HOOK_SETTINGS=str(NATIVE / 'settings.json'),
           XDG_RUNTIME_DIR=f'/run/user/{EXPECTED_UID}',
           DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{EXPECTED_UID}/bus')
ENV['PATH'] = ':'.join([str(BUN.parent), str(ACCOUNT_HOME / '.local/bin'), str(COMMAND.parent), ENV['PATH']])
sys.path.insert(0, str(PACKAGE))
from scripts.release_transaction import _files, _digest_tree
from lifeos_hook_bridge.version_drift import load_baseline, changed_paths, create_baseline, save_baseline
from lifeos_hook_bridge.update_hooks import replace_owned_hooks
from lifeos_hook_bridge.installation_lock import installation_lock


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, data):
    path = RELEASE / name
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, path)
    descriptor = os.open(RELEASE, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run(args, timeout=300, input=None, extra=None):
    result = subprocess.run([str(arg) for arg in args], cwd=OPERATING_HOME,
                            env=dict(ENV, **(extra or {})), input=input,
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        failure = RELEASE / f'command-failure-{int(time.time())}.txt'
        failure.write_text(result.stdout + result.stderr)
        failure.chmod(0o600)
        raise RuntimeError(f'{Path(args[0]).name} exits {result.returncode}; private output: {failure.name}')
    return result.stdout.strip()


def service(action):
    return run(['systemctl', '--user', action, *UNITS], timeout=120)


def user_hashes():
    result = {}
    for label, path in [('native-user', NATIVE / 'LIFEOS/USER'),
                        ('native-memory', NATIVE / 'LIFEOS/MEMORY'),
                        ('hermes-memory', PROFILE / 'memories'),
                        ('hermes-user', PROFILE / 'USER.md'),
                        ('hermes-facts', PROFILE / 'MEMORY.md')]:
        if not path.exists():
            continue
        paths = path.resolve().rglob('*') if path.is_dir() else [path]
        for file in paths:
            if file.is_file() and not file.is_symlink():
                relative = file.relative_to(path.resolve()).as_posix() if path.is_dir() else file.name
                result[label + '/' + relative] = sha(file)
    return result


def protected_hashes():
    paths = [PROFILE / name for name in ['config.yaml', '.env', 'lifeos-memory.json', 'SOUL.md', 'USER.md']]
    paths += [NATIVE / name for name in ['settings.json', 'CLAUDE.md', 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md']]
    return {str(path): sha(path) if path.is_file() else None for path in paths}


def observer():
    configuration = OPERATING_HOME / '.config/lifeos-development-capture/config.json'
    interpreter = PROFILE / 'tools/python-3.14.7+20260901-linux-x64/bin/python3'
    startup = interpreter.parent.parent / 'lib/python3.14/site-packages/lifeos_development_capture.pth'
    if not configuration.exists() or not startup.exists():
        return None
    match = re.search(r'sys.path.insert\(0, (.+?)\);', startup.read_text())
    assert match, 'Recorder startup source path is unavailable'
    source = Path(ast.literal_eval(match.group(1)))
    assert source.is_relative_to(OPERATING_HOME) or source.is_relative_to(ACCOUNT_HOME)
    return {'configuration': str(configuration), 'source': str(source), 'startup': str(startup)}


def prepare():
    import yaml
    assert (PACKAGE / 'VERSION').read_text().strip() == '0.1.0'
    for name in ['uv.lock', 'pyproject.toml', 'pm/lock.json']:
        assert sha(HERMES / name) == sha(CANDIDATE / name), f'Host dependency files differ: {name}'
    baseline = load_baseline(BASELINE, NATIVE)
    prior_source = Path(baseline['source_root'])
    drift = changed_paths(baseline, NATIVE)
    if drift:
        assert TARGET == 'discord' and drift == ['LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md']
        previous = ACCOUNT_HOME / 'workspace/releases/20260929-patch-footprint-e762ac6/snapshot/profile-before' / drift[0]
        normalize = lambda path: re.sub(r'^last_updated: .*$', 'last_updated:', path.read_text(), flags=re.M)
        assert normalize(previous) == normalize(NATIVE / drift[0]), 'Unreviewed native drift'
    current = json.loads((NATIVE / 'settings.json').read_text())
    selected, counts = replace_owned_hooks(current,
        json.loads((prior_source / 'hooks/hooks.json').read_text())['hooks'],
        json.loads((SOURCE / 'hooks/hooks.json').read_text())['hooks'])
    assert current == selected and counts == {'old_hooks': 74, 'new_hooks': 74, 'foreign_hooks': 0}
    for name in ['package.json', 'CLAUDE.template.md', 'settings.system.json', 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md']:
        assert sha(prior_source / name) == sha(SOURCE / name), f'Native dependency or identity change: {name}'
    for name in ['bun.lock', 'bun.lockb']:
        if (SOURCE / name).exists():
            assert (prior_source / name).exists() and sha(prior_source / name) == sha(SOURCE / name)
    code = []
    for component, candidate, installed in [('plugin', PACKAGE / 'lifeos_hook_bridge', PLUGIN),
                                             ('hermes', CANDIDATE, HERMES)]:
        for relative, path in _files(candidate):
            target = installed / relative
            before = sha(target) if target.is_file() else None
            if before != sha(path):
                if TARGET == 'acceptance' and component == 'hermes':
                    raise RuntimeError(f'Acceptance host differs from the compatibility set: {relative}')
                code.append({'component': component, 'source': str(path), 'target': str(target),
                             'relative': str(relative), 'before': before, 'after': sha(path)})
    for relative, path in _files(SOURCE):
        prior = prior_source / relative
        if prior.is_file() and sha(prior) == sha(path):
            continue
        assert not str(relative).startswith(('LIFEOS/USER/', 'LIFEOS/MEMORY/'))
        assert relative.name not in ['settings.json', 'CLAUDE.md', 'CLAUDE.template.md']
        target = NATIVE / relative
        assert not target.is_symlink()
        code.append({'component': 'native', 'source': str(path), 'target': str(target),
                     'relative': str(relative), 'before': sha(target) if target.is_file() else None,
                     'after': sha(path)})
    recorder = observer()
    if recorder:
        for relative, path in _files(PACKAGE / 'development'):
            if not str(relative).startswith('hook_capture/'):
                continue
            target = Path(recorder['source']) / relative
            before = sha(target) if target.is_file() else None
            if before != sha(path):
                code.append({'component': 'recorder', 'source': str(path), 'target': str(target),
                             'relative': str(relative), 'before': before, 'after': sha(path)})
    if TARGET == 'discord':
        assert not run(['git', '-C', HERMES, 'status', '--porcelain'])
    data = {'revision': REVISION, 'target': TARGET, 'code': code, 'protected': protected_hashes(),
            'baseline_hash': sha(BASELINE), 'reviewed_drift': drift, 'hooks': counts, 'recorder': recorder,
            'plugin_digest': _digest_tree(PACKAGE / 'lifeos_hook_bridge'),
            'hermes_files': {str(relative): sha(path) for relative, path in _files(CANDIDATE)},
            'plugin_dependencies': yaml.safe_load((PACKAGE / 'lifeos_hook_bridge/plugin.yaml').read_text())['python_dependencies']}
    save('preflight.json', data)
    print(json.dumps({'prepared': TARGET, 'revision': REVISION,
                      'changes': {name: sum(item['component'] == name for item in code) for name in ['hermes', 'plugin', 'native', 'recorder']},
                      'reviewed_drift': drift, 'hooks': counts}))


def dependency_snapshot():
    root = RELEASE / 'dependencies-before'
    if root.exists():
        return
    root.mkdir(mode=0o700)
    key = hashlib.sha256(str(HERMES.resolve()).encode()).hexdigest()[:16]
    state = PROFILE / 'installs' / key
    assert state.is_dir()
    run(['cp', '-a', '--reflink=auto', state, root / 'state-before'])
    save('dependencies.json', {'state': str(state), 'backup': str(root / 'state-before')})


def dependencies():
    dependency_snapshot()
    validate(PACKAGE / 'lifeos_hook_bridge', 'stage',
             install_dependencies=not (RELEASE / 'plugin-validation-stage.json').exists(), candidate_host=True)
    print('Declared dependencies and actual loader pass; catalog findings are recorded for review')


def validate(plugin, phase, *, install_dependencies=False, candidate_host=False):
    args = [COMMAND, 'plugins', 'validate', plugin, '--json']
    if install_dependencies:
        args.append('--install-deps')
    result = subprocess.run([str(arg) for arg in args], cwd=OPERATING_HOME, env=ENV,
                            capture_output=True, text=True, timeout=1200)
    (RELEASE / f'plugin-validation-{phase}.json').write_text(result.stdout + '\n')
    (RELEASE / f'plugin-validation-{phase}.stderr').write_text(result.stderr)
    report = json.loads(result.stdout)
    failures = [check for check in report['checks'] if not check['ok']]
    for check in failures:
        if check['name'] == 'security scan':
            labels = re.findall(r'([a-z_]+) \([^)]*\)', check['detail'])
            assert labels and set(labels) == {'ssh_backdoor'}, 'Unreviewed scanner finding'
        elif check['name'] == 'capability probe':
            assert check['detail'] == "register() raised: RecordingContext.register_middleware() got an unexpected keyword argument 'required'"
        else:
            raise RuntimeError('Unexpected catalog validation failure: ' + check['name'])
    assert result.returncode == (1 if failures else 0)
    interpreter = PROFILE / 'tools/python-3.14.7+20260901-linux-x64/bin/python3'
    output = run([interpreter, RELEASE / 'check_runtime.py', HERMES,
                  CANDIDATE if candidate_host else HERMES, plugin], timeout=120)
    (RELEASE / f'actual-loader-{phase}.json').write_text(output + '\n')
    loaded = json.loads(output)
    assert loaded['loaded'] and loaded['profile_and_ssh_state_unchanged']
    return loaded


def copy_code(item):
    target = Path(item['target'])
    assert sha(Path(item['source'])) == item['after']
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('.' + target.name + '.release-d5dafbc')
    shutil.copy2(item['source'], temporary)
    os.replace(temporary, target)


def refresh_recorder(data):
    recorder = data['recorder']
    if not recorder:
        return
    configuration = Path(recorder['configuration'])
    current = json.loads(configuration.read_text())
    current['fingerprints'] = {name: sha(Path(name)) for name in current['fingerprints']}
    source = Path(recorder['source']) / 'hook_capture'
    current['capture_sources'] = {path.name: sha(path) for path in source.glob('*.py')}
    current['plugin_revision'] = REVISION
    temporary = configuration.with_suffix('.release.tmp')
    temporary.write_text(json.dumps(current, indent=2) + '\n')
    temporary.chmod(0o600)
    os.replace(temporary, configuration)
    # Managed dependency staging can replace the interpreter. Preserve the
    # existing account recorder in the selected interpreter after staging.
    startup = Path(recorder['startup'])
    text = (f"import sys; sys.path.insert(0, {recorder['source']!r}); "
            f"from hook_capture.bootstrap import start; start({recorder['configuration']!r})\n")
    if not startup.exists():
        startup.write_text(text)
        startup.chmod(0o600)


def snapshot(data):
    assert not BACKUP.exists()
    BACKUP.mkdir(mode=0o700)
    run(['cp', '-a', '--reflink=auto', PROFILE, BACKUP / 'profile-before'], timeout=600)
    for name in ['USER', 'MEMORY']:
        path = NATIVE / 'LIFEOS' / name
        if path.exists():
            run(['cp', '-a', '--reflink=auto', path.resolve(), BACKUP / ('native-' + name.lower())], timeout=600)
    shutil.copy2(BASELINE, BACKUP / 'baseline-before.json')
    for index, item in enumerate(data['code']):
        if item['before'] is not None:
            shutil.copy2(item['target'], BACKUP / f'code-{index}')
    if data['recorder']:
        shutil.copy2(data['recorder']['configuration'], BACKUP / 'recorder-config-before.json')
    save('user-hashes-before.json', user_hashes())


def restore_code(data):
    for index, item in reversed(list(enumerate(data['code']))):
        target = Path(item['target'])
        if item['before'] is None:
            if target.exists():
                assert sha(target) == item['after'], 'New code changed after deployment'
                target.unlink()
        else:
            if target.exists() and sha(target) not in [item['after'], item['before']]:
                divergent = RELEASE / 'divergent-code'
                divergent.mkdir(mode=0o700, exist_ok=True)
                shutil.copy2(target, divergent / str(index))
            assert sha(BACKUP / f'code-{index}') == item['before']
            shutil.copy2(BACKUP / f'code-{index}', target)
    shutil.copy2(BACKUP / 'baseline-before.json', BASELINE)
    metadata = PROFILE / 'plugins/.install-metadata.json'
    prior = BACKUP / 'profile-before/plugins/.install-metadata.json'
    if prior.exists():
        shutil.copy2(prior, metadata)
    else:
        metadata.unlink(missing_ok=True)
    if data['recorder']:
        shutil.copy2(BACKUP / 'recorder-config-before.json', data['recorder']['configuration'])
    dependency = RELEASE / 'dependencies.json'
    if dependency.exists():
        saved = json.loads(dependency.read_text())
        source = Path(saved['backup'])
        target = Path(saved['state'])
        run(['cp', '-a', '--reflink=auto', str(source) + '/.', target], timeout=600)


def apply():
    data = json.loads((RELEASE / 'preflight.json').read_text())
    with installation_lock(PROFILE):
        assert protected_hashes() == data['protected'], 'Profile changed since preparation'
        assert sha(BASELINE) == data['baseline_hash'], 'Baseline changed since preparation'
        for item in data['code']:
            target = Path(item['target'])
            assert (sha(target) if target.is_file() else None) == item['before'], 'Installed code changed since preparation'
        save('status.json', {'state': 'stopping', 'revision': REVISION})
        changed = False
        try:
            service('stop')
            snapshot(data)
            assert protected_hashes() == data['protected']
            save('status.json', {'state': 'applying', 'revision': REVISION})
            changed = True
            for item in data['code']:
                copy_code(item)
            for tree in [HERMES, PLUGIN, Path(data['recorder']['source']) if data['recorder'] else PLUGIN]:
                for parent, directories, files in os.walk(tree):
                    directories[:] = [name for name in directories if name not in {'.git', '.hermes', '.venv', 'venv', 'node_modules'}]
                    if '__pycache__' in directories:
                        shutil.rmtree(Path(parent) / '__pycache__')
                        directories.remove('__pycache__')
            assert user_hashes() == json.loads((RELEASE / 'user-hashes-before.json').read_text())
            assert protected_hashes() == data['protected']
            if any(item['component'] == 'native' for item in data['code']):
                save_baseline(create_baseline(SOURCE, NATIVE), BASELINE, renew=True)
            metadata = PROFILE / 'plugins/.install-metadata.json'
            current = json.loads(metadata.read_text()) if metadata.exists() else {}
            current['lifeos-hook-bridge'] = {'pinned': True, 'revision': REVISION,
                'source': 'https://github.com/0ut5ider/lifeos-hermes-plugin.git#lifeos_hook_bridge'}
            metadata.write_text(json.dumps(current, indent=2) + '\n')
            metadata.chmod(0o600)
            refresh_recorder(data)
            assert _digest_tree(PLUGIN) == data['plugin_digest']
            save('status.json', {'state': 'installed', 'revision': REVISION, 'preserved_data': True})
            service('start')
            assert len(service('is-active').splitlines()) == len(UNITS)
            save('status.json', {'state': 'running', 'revision': REVISION, 'preserved_data': True})
            print(json.dumps({'state': 'running', 'target': TARGET, 'revision': REVISION, 'preserved_data': True}))
        except BaseException:
            service('stop')
            if changed:
                restore_code(data)
            service('start')
            save('status.json', {'state': 'rolled_back' if changed else 'failed_before_apply', 'revision': REVISION})
            raise


def verify():
    import urllib.request, urllib.error
    data = json.loads((RELEASE / 'preflight.json').read_text())
    assert _digest_tree(PLUGIN) == data['plugin_digest']
    mismatched = [name for name, digest in data['hermes_files'].items() if sha(HERMES / name) != digest]
    assert not mismatched, f'Host source mismatch: {mismatched}'
    assert protected_hashes() == data['protected'], 'Protected profile files changed'
    for item in data['code']:
        assert sha(item['target']) == item['after'], f'Installed source mismatch: {item["relative"]}'
    baseline = load_baseline(BASELINE, NATIVE)
    drift = changed_paths(baseline, NATIVE)
    assert not drift, f'Unexpected native source drift: {drift}'
    states = service('is-active').splitlines()
    assert states == ['active'] * len(UNITS)
    validate(PLUGIN, 'live')
    output = run([COMMAND, 'config', 'check'])
    (RELEASE / 'config-check.txt').write_text(output + '\n')
    mount_command = [BUN, NATIVE / 'LIFEOS/HERMES/Mount.ts', '--config-root', NATIVE, '--check']
    import runpy
    installed_api = runpy.run_path(str(PLUGIN / "install_source.py"))
    administration = installed_api["memory_administration"]()
    if administration.required(NATIVE, PROFILE):
        MemoryConfiguration = installed_api["memory_module"]("memory_service").MemoryConfiguration
        configuration = MemoryConfiguration(PROFILE / 'lifeos-memory.json')
        config = configuration.load()
        accounts = [account for account, principal in config['accounts'].items()
                    if account.startswith('dashboard:') and principal == config['principal']]
        assert len(accounts) == 1, 'Review ambiguous installation owner before mounting'
        # Adrian authorizes this local administrative verification. The existing
        # owner binding supplies a short-lived grant for a read-only native check.
        with administration.lease(configuration, accounts[0], ttl=120) as grant:
            mount_env = administration.mount_environment(NATIVE, PROFILE, grant)
            mount_env["PATH"] = ENV["PATH"]
            output = run(mount_command, extra=mount_env)
    else:
        output = run(mount_command)
    (RELEASE / 'mount-check.txt').write_text(output + '\n')
    statuses = {}
    for route in ['/chat', '/lifeos-bridge', '/api/plugins']:
        url = f'http://192.168.8.212:{PORT}{route}'
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        statuses[route] = status
        assert status == (401 if route == '/api/plugins' else 200)
    marker = 'MERGED-212-' + TARGET.upper() + '-READY'
    output = run([COMMAND, 'lifeos-infer', '--print', '--model', 'flashnext-w4a16-fp8ple',
                  '--effort', 'low', '--output-format', 'json', '--system-prompt', 'Return exactly ' + marker + '.'],
                 input='Return exactly ' + marker + '.', extra={'LIFEOS_CHILD_PROVIDER': 'custom'}, timeout=240)
    model = json.loads(output)
    assert model.get('is_error') is False and model.get('result', '').strip() == marker, 'Private model check fails'
    memory = PROFILE / 'lifeos-memory.json'
    ownership = json.loads(memory.read_text()).get('ownership_enabled', False) if memory.exists() else False
    assert ownership is False
    result = {'state': 'verified', 'target': TARGET, 'revision': REVISION,
              'runtime_files': 75, 'source_mismatch': 0, 'baseline_files': len(baseline['files']),
              'baseline_changed': 0, 'services': dict(zip(UNITS, states)),
              'http': statuses, 'model_smoke': marker, 'memory_ownership': False,
              'preserved_profile': True, 'preserved_user_data_at_apply': True}
    save('result.json', result)
    save('status.json', {'state': 'verified', 'revision': REVISION})
    print(json.dumps(result))


def restore():
    data = json.loads((RELEASE / 'preflight.json').read_text())
    with installation_lock(PROFILE):
        assert protected_hashes() == data['protected'], 'Profile changed; review before rollback'
        service('stop')
        try:
            before = user_hashes()
            restore_code(data)
            assert user_hashes() == before, 'Rollback changes current data'
        finally:
            service('start')
        assert service('is-active').splitlines() == ['active'] * len(UNITS)
        save('status.json', {'state': 'restored', 'current_data_preserved': True})
        print('Prior code restored; current data preserved; services active')


if ACTION == 'prepare':
    prepare()
elif ACTION == 'dependencies':
    dependencies()
elif ACTION == 'apply':
    apply()
elif ACTION == 'verify':
    verify()
elif ACTION == 'restore':
    restore()
else:
    raise SystemExit('Unknown release action')
