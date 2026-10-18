# ABOUTME: Prepares an in-place LifeOS operation for the owner's existing Hermes installation.
# ABOUTME: Downloads the integration, stages host patches and LifeOS, and records the reviewed request.
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .host_compatibility import check, load_manifest
from .host_patches import stage_host_files
from .host_record import check_originals, load_record
from .integration_package import COMPATIBILITY, validate_integration
from .release_accounts import account_home
from .release_catalog import ReleaseCatalog, ReleaseRejected, parse_json, extract_package
from .release_programs import publish
from .release_stage import stage_environment, load_bridge, run_stage, runtime_source_fingerprint, sha, user_runtime_directory
from .release_tools import prepare_bun


def _first_reason(result):
    reasons = result['reasons']
    return reasons[0]['message'] if reasons else 'The Hermes installation is not in the required state.'


def host_python(source):
    """Return the interpreter of the dependency environment that Hermes selected for ``source``."""
    from pm.environments import selected_venv, venv_python
    python = venv_python(selected_venv(Path(source)))
    if not python.is_file():
        raise ReleaseRejected('The Hermes installation has no selected Python environment')
    return python


def host_launcher(source):
    launcher = Path(source) / '.hermes/bin/hermes'
    if launcher.is_symlink() or not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise ReleaseRejected('The Hermes installation has no source launcher')
    return launcher


GATEWAY_UNIT = '.config/systemd/user/hermes-gateway.service'
TRANSITION_GATEWAY = 'transition-gateway.service'


MANAGED_RUNTIME = '/.lifeos-releases/'


def _unit_texts(home, name):
    """Return ``{path: text}`` for a user unit and its drop-ins."""
    directory = Path(home) / '.config/systemd/user'
    paths = [directory / name, *sorted((directory / (name + '.d')).glob('*.conf'))]
    return {path: path.read_text(errors='replace') for path in paths if path.is_file()}


def _service_value(text, key, default):
    """Return the last ``key=`` value in the ``[Service]`` section, as systemd applies the last assignment."""
    section, values = None, []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            section = stripped
        elif section == '[Service]' and stripped.startswith(key + '='):
            values.append(stripped.split('=', 1)[1].strip())
    return values[-1] if values else default


ACCOUNT_COMMANDS = ('hermes', 'hermes-agent', 'hermes-acp')
FORWARDER_BYTES = 1024 * 1024
UNIT_COMMANDS = ('ExecStartPre', 'ExecStart', 'ExecStartPost')


def _runs_managed_runtime(path):
    """True when ``path`` is in the managed runtime or is a small script that names it."""
    if MANAGED_RUNTIME in str(path):
        return True
    try:
        if not path.is_file() or path.stat().st_size > FORWARDER_BYTES:
            return False
        return MANAGED_RUNTIME.encode() in path.read_bytes()
    except OSError:
        raise ReleaseRejected('Preparation cannot read ' + str(path) + ', which a Hermes unit runs') from None


def _command_programs(entry):
    """Return the program and the arguments of one command that ``systemctl show`` reports."""
    paths = re.findall(r'\bpath=([^ ;}]+)', entry)
    arguments = [part.strip('\'"') for value in re.findall(r'\bargv\[\]=(.*?) ; ignore_errors=', entry)
                 for part in value.split()]
    return paths + arguments


def _check_replaced_drop_ins(unit, values):
    """Refuse a drop-in that sets a command for a unit the transition replaces, because the drop-in stays."""
    for value in values.get('DropInPaths', '').split():
        try:
            text = Path(value).read_text(errors='replace')
        except OSError:
            raise ReleaseRejected('Preparation cannot read the ' + unit + ' drop-in ' + value) from None
        if re.search(r'^\s*Exec', text, re.MULTILINE):
            raise ReleaseRejected('The ' + unit + ' drop-in ' + value + ' sets a command, and the transition replaces '
                                  'that unit. Remove the command from the drop-in, then prepare again.')


def check_service_launchers(home, *, replaced=()):
    """Refuse a transition while a Hermes unit still runs the managed runtime after it.

    The transition repoints only the account commands in ``~/.local/bin`` and replaces the units in
    ``replaced``. Any other program that a unit runs, such as a forwarder inside another Hermes checkout,
    would keep running the managed runtime, and its own checkout can rewrite it later. The service manager
    reports each command after drop-ins and specifiers apply.
    """
    from .inplace_services import UNITS, show
    account = {Path(home) / '.local/bin' / name for name in ACCOUNT_COMMANDS}
    for role, unit in UNITS.items():
        values = show(unit, 'LoadState', 'DropInPaths', *UNIT_COMMANDS)
        if values.get('LoadState') != 'loaded':
            continue
        if role in replaced:
            _check_replaced_drop_ins(unit, values)
            continue
        if not re.search(r'\bpath=', values.get('ExecStart', '')):
            raise ReleaseRejected('The service manager reports no command for ' + unit)
        for key in UNIT_COMMANDS:
            for entry in values.get(key, '').splitlines():
                for value in _command_programs(entry):
                    path = Path(value)
                    if path.is_absolute() and path not in account and _runs_managed_runtime(path):
                        raise ReleaseRejected('The ' + unit + ' unit runs ' + value + ', which runs the managed '
                                              'runtime. Point the unit at ~/.local/bin/hermes, run `systemctl --user '
                                              'daemon-reload`, then prepare again.')


def transition_gateway_unit(python, source, profile, home, job):
    """Write the gateway unit that stock Hermes generates for ``source`` and return its reviewed hashes.

    A managed runtime's gateway unit can run the managed launcher. The transition replaces such a unit
    with the unit that ``hermes gateway install`` would write for the stock checkout. A unit that runs
    the account launcher needs no replacement, because the transition repoints that launcher. A drop-in
    or another unit that still runs the managed runtime refuses the transition, as does a replacement
    whose stop behaviour or working directory differs, because the service controller binds those.
    """
    from .inplace_services import UNITS
    for name in UNITS.values():
        for path, text in _unit_texts(home, name).items():
            if MANAGED_RUNTIME in text and not (name == 'hermes-gateway.service' and path.name == name):
                raise ReleaseRejected('The ' + path.name + ' unit runs the managed runtime; point it at ~/.local/bin first')
    existing = Path(home) / GATEWAY_UNIT
    if existing.is_symlink():
        raise ReleaseRejected('The gateway unit must be a regular file before the transition')
    replace = existing.is_file() and MANAGED_RUNTIME in existing.read_text(errors='replace')
    check_service_launchers(home, replaced=('gateway',) if replace else ())
    if not replace:
        return {}
    environment = {key: value for key, value in os.environ.items()
                   if key not in {'LD_LIBRARY_PATH', 'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'}}
    environment.update(HOME=str(home), HERMES_HOME=str(profile))
    script = ('import sys\nsys.path.insert(0, sys.argv[1])\n'
              'from hermes_cli.gateway import generate_systemd_unit\nsys.stdout.write(generate_systemd_unit())\n')
    result = subprocess.run([str(python), '-I', '-B', '-c', script, str(source)], capture_output=True, text=True,
                            env=environment, cwd=str(profile), timeout=120)
    if result.returncode or MANAGED_RUNTIME in result.stdout or 'ExecStart=' not in result.stdout:
        detail = (result.stderr.strip().splitlines() or [''])[-1][:300]
        raise ReleaseRejected('Stock Hermes does not generate a gateway unit for the installation' + (': ' + detail if detail else ''))
    current = existing.read_text(errors='replace')
    for key, default in (('KillMode', 'control-group'), ('WorkingDirectory', '')):
        if _service_value(current, key, default) != _service_value(result.stdout, key, default):
            raise ReleaseRejected('The stock gateway unit changes ' + key + '; install the stock unit with '
                                  '`hermes gateway install` before the transition')
    target = Path(job) / TRANSITION_GATEWAY
    publish(target, result.stdout.encode())
    return {'gateway': {'before': sha(existing), 'after': sha(target)}}


def state_directory(source):
    from pm.environments import install_state_dir
    return install_state_dir(Path(source))


def desired_host_files(entry, staged, record=None, originals=None):
    """Map each host target to its desired file after the operation, or None for an absent file.

    Targets of the new entry receive their staged patched file. Targets that only the recorded release
    changed return to their retained original, or to absence when that release added them.
    """
    desired = {relative: paths['patched'] for relative, paths in staged.items()}
    if record is not None:
        for relative, hashes in record['files'].items():
            if relative not in desired:
                desired[relative] = None if hashes['stock'] is None else originals[relative]
    return desired


def stock_source(source, record, originals, entry, destination):
    """Assemble the stock files of ``entry`` for an installed host: retained originals, plus unpatched host files.

    A target that the recorded release did not change is still stock on the host, so it is read from there;
    staging verifies every copied file against its stock hash.
    """
    destination = Path(destination)
    destination.mkdir(mode=0o700)
    for relative, hashes in entry['files'].items():
        if hashes['stock'] is None:
            continue
        if relative in originals:
            origin = originals[relative]
        elif relative in record['files']:
            raise ReleaseRejected('The host record and the release disagree about an original Hermes file: ' + relative)
        else:
            origin = Path(source) / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    return destination


def build_preview(source, desired, destination):
    """Copy the tracked Hermes files, then overlay the desired host files, for preparation checks only."""
    source, destination = Path(source), Path(destination)
    listed = subprocess.run(['git', '--no-optional-locks', '-C', str(source), 'ls-files', '-z'],
                            capture_output=True, timeout=120, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if listed.returncode:
        raise ReleaseRejected('Git cannot list the Hermes source files')
    destination.mkdir(mode=0o700)
    for name in listed.stdout.split(b'\0'):
        if not name:
            continue
        relative = name.decode()
        target = destination / relative
        origin = source / relative
        if origin.is_symlink() or not origin.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    for relative, path in desired.items():
        target = destination / relative
        if path is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return destination


def resolve_dependencies(job, python, source, profile, bridge):
    """Lock the bridge with the enabled plugins in a throwaway workspace under the host interpreter."""
    output = job / 'dependency-resolution.json'
    environment = {**stage_environment(Path(profile), home=account_home(profile), source=Path(source)),
                   'XDG_RUNTIME_DIR': user_runtime_directory()}
    run_stage([python, '-B', Path(__file__).with_name('dependency_plan.py'), 'resolve', source, profile, bridge,
               job / 'dependency-workspace', output], job, 'dependency-resolution', environment=environment)
    return parse_json(output.read_bytes())


def prepare_inplace(profile, job, version=None, *, name, assistant, intent, catalog=None):
    """Prepare the reviewed in-place request in ``job``; the active installation is not changed."""
    profile, job = Path(profile), Path(job)
    home = account_home(profile)
    result = check(profile)
    if result['state'] not in {'compatible', 'installed'}:
        raise ReleaseRejected('LifeOS cannot be installed on this Hermes installation: ' + _first_reason(result))
    record = load_record(profile)
    downloaded = (catalog or ReleaseCatalog()).download_integration(job / 'download', version)
    source = Path(result['detected']['source'])
    certificate = downloaded['certificate']
    package = job / 'package'
    extract_package(downloaded['archive'], package)
    manifest = validate_integration(package, certificate)
    entry = next((item for item in load_manifest(package / COMPATIBILITY)['hermes']
                  if item['commit'] == result['detected']['commit']), None)
    if entry is None:
        raise ReleaseRejected('This LifeOS release does not support the installed Hermes version')
    bridge = load_bridge(package / 'lifeos_hook_bridge')
    names = bridge.memory_module('fresh_store')
    names._name(name)
    names._name(assistant)
    selected = bridge.memory_module('lifeos_installation').selection(profile)
    fresh = not selected.installed.exists() and not selected.installed.is_symlink()
    if intent == 'install' and (not fresh or record is not None):
        raise ReleaseRejected('Use an update for the existing LifeOS installation')
    if result['transition'] and (fresh or record is not None or intent == 'install'):
        raise ReleaseRejected('Moving from a managed runtime requires the installed managed release and an update')
    if intent in {'update', 'plugin'} and fresh:
        raise ReleaseRejected('Install LifeOS before requesting an update')
    if fresh:
        from .release_services import require_fresh_services
        require_fresh_services(bridge)
    if bridge.SUPPORTED_LIFEOS_COMMIT != certificate['lifeos']['commit']:
        raise ReleaseRejected('The integration bridge pins another LifeOS commit than its certificate')
    patches = package / 'lifeos_hook_bridge/patches'
    originals = None
    if record is not None:
        originals = check_originals(record)
        staged = stage_host_files(stock_source(source, record, originals, entry, job / 'host-source'),
                                  entry, patches, job / 'host')
    else:
        staged = stage_host_files(source, entry, patches, job / 'host')
    desired = desired_host_files(entry, staged, record, originals)
    lifeos = bridge.prepare_lifeos(certificate['lifeos']['upstream'], job / 'lifeos', certificate['lifeos']['commit'],
                                   patches, bridge.LIFEOS_PATCHES, expected_tree=certificate['lifeos']['tree_sha256'])
    dependencies = parse_json((package / 'lifeos_hook_bridge/dependency_locks/catalog.json').read_bytes())
    (job / 'tools').mkdir(mode=0o700)
    bun = prepare_bun(job / 'tools', package / 'optional/lifeos_release_manager/release-tools.json',
                      dependencies['bun_version'])
    python = host_python(source)
    preview = build_preview(source, desired, job / 'hermes-preview')
    # The installed host must expose these capabilities after restart; the preview proves the patches provide them.
    from .host_capabilities import probe_capabilities
    probe_capabilities(python, preview, entry, environment={**os.environ, 'HOME': str(home), 'HERMES_HOME': str(profile)})
    dependencies = resolve_dependencies(job, python, source, profile, package / 'lifeos_hook_bridge')
    if dependencies['changed']:
        raise ReleaseRejected('LifeOS would change installed Python packages: ' + ', '.join(sorted(dependencies['changed'])))
    reference = job / 'reference-home'
    reference.mkdir(mode=0o700)
    script = ('import importlib.util,sys\nfrom pathlib import Path\n'
        'spec=importlib.util.spec_from_file_location("lifeos_release_install",Path(sys.argv[1])/"install_source.py")\n'
        'source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)\n'
        'source.install_lifeos(Path(sys.argv[2]),Path(sys.argv[3])/".claude",Path(sys.argv[3])/"failed",'
        'sys.argv[4],source.SUPPORTED_LIFEOS_COMMIT,Path(sys.argv[1])/"patches",source.LIFEOS_PATCHES)\n')
    environment = stage_environment(job / 'reference-profile', home=reference, source=preview)
    (job / 'reference-profile').mkdir(mode=0o700)
    environment['PATH'] = str(job / 'tools') + os.pathsep + environment.get('PATH', os.defpath)
    run_stage([python, '-B', '-c', script, package / 'lifeos_hook_bridge', job / 'lifeos', reference, bun],
              job, 'native-dependencies', environment=environment, timeout=1800)
    request = {
        'format': 2, 'identifier': job.name, 'profile': str(profile), 'account_home': str(home),
        'installed': str(selected.installed), 'version': manifest['version'], 'commit': manifest['head'],
        'package_sha256': sha(downloaded['archive']), 'certificate': certificate,
        'configuration_sha256': sha(profile / 'config.yaml'),
        'host': {'source': str(source), 'commit': entry['commit'], 'label': entry['label'],
                 'state': result['state'], 'state_directory': str(state_directory(source)),
                 'transition': result['transition'],
                 'transition_units': transition_gateway_unit(python, source, profile, home, job) if result['transition'] else {},
                 'record_sha256': None if record is None else sha(profile / 'lifeos-host.json')},
        'runtime': {'python': str(python), 'bun': str(bun), 'hermes': str(host_launcher(source)),
                    'source': str(preview), 'reference': str(reference / '.claude'),
                    'lifeos': str(job / 'lifeos'), 'host_files': str(job / 'host')},
        'name': name, 'assistant': assistant, 'lifeos_tree_sha256': lifeos['tree_sha256'],
        'runtime_fingerprint': runtime_source_fingerprint(preview), 'dependencies': dependencies,
    }
    publish(job / 'request.json', (json.dumps(request, indent=2) + '\n').encode())
    shutil.copytree(package / 'optional/lifeos_release_manager', job / 'worker',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return request, manifest
