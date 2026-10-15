# ABOUTME: Builds a committed integration package with pinned native sources and a frozen Python closure.
# ABOUTME: Records candidate identities without publishing a qualification certificate or selecting live code.
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


def file_map(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def build(args):
    repo = Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo).strip():
        raise ValueError('Commit tracked changes before package preparation')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    version = (repo / 'VERSION').read_text().strip()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=True)
    package = args.output / (version + '-' + head[:8])
    package.mkdir(mode=0o700)
    selected = ['lifeos_hook_bridge', 'optional', 'scripts', 'tests', 'docs/deployment/daily-text',
                'VERSION', 'CHANGELOG.md', 'README.md',
                'docs/verification/2026-10-11-daily-guest/deliver_morning.py']
    data = subprocess.check_output(['git', 'archive', head, '--', *selected], cwd=repo)
    with tarfile.open(fileobj=io.BytesIO(data)) as source:
        source.extractall(package, filter='data')
    sys.path.insert(0, str(package))
    from lifeos_hook_bridge import install_source, release_version
    if release_version.versions(package) != version:
        raise ValueError('Integration version declarations differ')
    hermes = install_source.prepare_supported_hermes(args.hermes_source, package / 'hermes')
    from optional.lifeos_release_manager.stock_hermes import build_archive
    stock = build_archive(args.hermes_source, package / 'stock-hermes.tgz', hermes['base_commit'])
    lifeos = install_source.prepare_lifeos(str(args.lifeos_source), package / 'lifeos',
        install_source.SUPPORTED_LIFEOS_COMMIT, package / 'lifeos_hook_bridge/patches', install_source.LIFEOS_PATCHES)
    closure = package / 'python-runtime'
    closure.mkdir(mode=0o700)
    for name in ('pyproject.toml', 'uv.lock'):
        shutil.copy2(args.python_closure / name, closure / name)
    shutil.copytree(args.python_closure / 'plugin-deps', closure / 'plugin-deps',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    bridge = file_map(package / 'lifeos_hook_bridge')
    manifest = {'version': version, 'head': head, 'status': 'release_candidate',
        'stock_hermes': stock,
        'plugin_files': {'lifeos_hook_bridge/' + k: v for k, v in bridge.items()},
        'manager_files': file_map(package / 'optional/lifeos_release_manager'),
        'python_runtime_files': file_map(closure),
        'daily_configuration_files': {'docs/deployment/daily-text/' + k: v for k, v in file_map(package / 'docs/deployment/daily-text').items()},
        'prepared_manifest_files': {name: hashlib.sha256((package / name).read_bytes()).hexdigest()
            for name in ('hermes/hermes-source-manifest.json', 'lifeos/lifeos-source-manifest.json')},
        'operators': {'morning': {'path': 'docs/verification/2026-10-11-daily-guest/deliver_morning.py',
            'sha256': hashlib.sha256((package / 'docs/verification/2026-10-11-daily-guest/deliver_morning.py').read_bytes()).hexdigest()}},
        'native_manifests_verified': True, 'combined_release_verified': False, 'live_selection_changed': False}
    (package / 'DAILY-CANDIDATE.json').write_text(json.dumps(manifest, indent=2) + '\n')
    archive = package.with_name(package.name + '.tgz')
    with tarfile.open(archive, 'x:gz') as target:
        for path in sorted(package.iterdir()):
            target.add(path, arcname=path.name, filter=lambda info: None if '__pycache__' in Path(info.name).parts else info)
    report = {'package': str(package), 'archive': str(archive), 'version': version, 'head': head,
        'archive_bytes': archive.stat().st_size, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'hermes_base': hermes['base_commit'], 'lifeos_base': lifeos['upstream_commit'],
        'hermes_patch_count': len(hermes['patches']), 'lifeos_patch_count': len(lifeos['patches']),
        'combined_release_verified': False, 'live_selection_changed': False}
    (args.output / (package.name + '-build.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('output', 'hermes-source', 'lifeos-source', 'python-closure'):
        parser.add_argument('--' + name, type=Path, required=True)
    os.umask(0o077)
    sys.dont_write_bytecode = True
    build(parser.parse_args())
