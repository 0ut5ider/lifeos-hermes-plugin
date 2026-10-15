# ABOUTME: Binds account-wide removal to an exact managed integration generation and native installation.
# ABOUTME: Refuses shared profiles, modified programs, and launchers outside the reviewed complete release.
import json
import os
from pathlib import Path
import re
import shlex

from .cli import profile_directory,read_private
from .release_accounts import account_home
from .release_catalog import ReleaseRejected
from .release_programs import fingerprint
from .release_stage import validate_package,validate_files,runtime_source_fingerprint


IDENTIFIER=re.compile('[0-9a-f]{32}')


def account(profile, installed):
    profile=profile_directory(profile);home=account_home(profile);installed=Path(installed).absolute()
    if profile!=home/'.hermes' or installed!=home/'.claude' or installed.resolve()!=installed or not installed.is_dir():
        raise ReleaseRejected('Complete removal requires one managed default profile and its account native home')
    profiles=profile/'profiles'
    if profiles.exists() or profiles.is_symlink():
        if profiles.resolve()!=profiles or not profiles.is_dir() or any(path.is_dir() or path.is_symlink() for path in profiles.iterdir()):
            raise ReleaseRejected('Another Hermes profile shares the account-wide program selection')
    return home


def _wrapper(path, command):
    expected=('#!/bin/sh\nexec '+shlex.quote(str(command))+' "$@"\n').encode()
    identity=fingerprint(path)
    if identity is None or identity['type']!='file' or path.read_bytes()!=expected:
        raise ReleaseRejected('An account launcher differs from the qualified integration generation')
    return identity


def selected(profile, installed, *, bridge):
    profile=profile_directory(profile);home=account(profile,installed)
    identity=read_private(profile/'integration-release.json')
    active=bridge.memory_module('release_version').status(profile,profile/'plugins/lifeos-hook-bridge')['active']
    if active['verification']!='verified':raise ReleaseRejected('The active bridge differs from its complete release')
    roots=profile/'.lifeos-releases'
    if roots.resolve()!=roots or not roots.is_dir():raise ReleaseRejected('The qualified integration generation is unavailable')
    candidates=[]
    for job in sorted(roots.iterdir()):
        if not IDENTIFIER.fullmatch(job.name):continue
        try:
            request=read_private(job/'request.json')
            current=read_private(job/'status.json')
        except FileNotFoundError:continue
        if (current['state']=='applied' and request.get('profile')==str(profile)
                and request.get('installed')==str(installed)
                and all(request.get(key)==identity.get(key) for key in ('version','commit','package_sha256'))):
            expected=('#!/bin/sh\nexec '+shlex.quote(str(job/'bin/hermes'))+' "$@"\n').encode()
            if (home/'.local/bin/hermes').read_bytes()==expected:candidates.append((job,request))
    if len(candidates)!=1:raise ReleaseRejected('Removal requires one exact currently selected complete generation')
    job,request=candidates[0];package=job/'package'
    validate_package(package,request['certificate'])
    if runtime_source_fingerprint(job/'hermes')!=request['runtime_fingerprint']:
        raise ReleaseRejected('The selected Hermes runtime differs from its qualified source')
    manifest=read_private(package/'DAILY-CANDIDATE.json')
    bridge_files={name.removeprefix('lifeos_hook_bridge/'):digest for name,digest in manifest['plugin_files'].items()}
    validate_files(profile/'plugins/lifeos-hook-bridge',bridge_files)
    validate_files(profile/'plugins/lifeos-release-manager',manifest['manager_files'])
    launchers={}
    for name in ('hermes','hermes-agent','hermes-acp'):
        path=home/'.local/bin'/name;launchers[path]=_wrapper(path,job/'bin'/name)
    programs=read_private(job/'program-snapshot/programs.json')
    for entry in programs['entries']:
        path=Path(entry['target'])
        if path in launchers or entry['kind']!='file' or entry['source'] is None:continue
        if Path(entry['source']).name=='hermes' and path.is_relative_to(home) and path.read_bytes().startswith(b'#!/bin/sh\nexec '):
            launchers[path]=_wrapper(path,job/'bin/hermes')
    bun=home/'.local/bin/bun'
    if fingerprint(bun)!=fingerprint(Path(request['runtime']['bun'])):
        raise ReleaseRejected('The account Bun command differs from its integration-owned program')
    return {'home':home,'job':job,'request':request,'package':package,'manifest':manifest,
        'bridge_files':bridge_files,'manager_files':manifest['manager_files'],'launchers':launchers,'bun':bun,'bun_identity':fingerprint(Path(request['runtime']['bun']))}
