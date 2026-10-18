# ABOUTME: Authenticates standalone software recovery with the actual Hermes dashboard password provider.
# ABOUTME: Issues the same exact owner workflow grant after the active manager has been removed.
import getpass
from pathlib import Path
import secrets
import sys
import types

if not __package__:
    package=types.ModuleType('lifeos_removal_recovery_manager')
    package.__path__=[str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__]=package
    __package__=package.__name__

from ruamel.yaml import YAML

from .release_catalog import ReleaseRejected


LOGIN_VARIABLES={'username':'HERMES_DASHBOARD_BASIC_AUTH_USERNAME','password_hash':'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH',
    'password':'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD'}
LOGIN_FILE_BYTES=1024*1024


def _private_bytes(path):
    """Return the bytes of an owner-only login source, refusing a shared or changing file."""
    from .release_programs import ProgramConflict, fingerprint
    try:
        identity=fingerprint(path)
    except ProgramConflict:
        identity=None
    if identity is None or identity['type']!='file' or identity['mode'] & 0o077 or Path(path).stat().st_size>LOGIN_FILE_BYTES:
        raise ReleaseRejected('Standalone recovery requires the private current dashboard configuration')
    data=Path(path).read_bytes()
    if fingerprint(path)!=identity:raise ReleaseRejected('The current dashboard configuration changes during authentication')
    return data


def _environment_file(path):
    import io
    from dotenv import dotenv_values
    return {key:value for key,value in dotenv_values(stream=io.StringIO(_private_bytes(path).decode())).items()
            if key in LOGIN_VARIABLES.values() and isinstance(value,str)}


def dashboard_unit_environment():
    """Return the dashboard unit's ``Environment=`` assignments and ``EnvironmentFiles=`` paths, or nothing."""
    import shlex
    from .inplace_services import show
    try:
        values=show('hermes-dashboard.service','LoadState','Environment','EnvironmentFiles')
    except ReleaseRejected:
        return [],[]
    if values.get('LoadState')!='loaded':
        return [],[]
    files=[Path(line.rsplit(' (ignore_errors=',1)[0]) for line in values.get('EnvironmentFiles','').splitlines() if line]
    return shlex.split(values.get('Environment','')),files


def _unit_login(unit):
    assignments,files=unit()
    found={}
    for item in assignments:
        key,_,value=item.partition('=')
        if key in LOGIN_VARIABLES.values():found[key]=value
    # systemd applies environment files after Environment= assignments.
    for path in files:
        found.update(_environment_file(path))
    return found


def basic_settings(profile,*,unit=None):
    """Return the dashboard password login as the dashboard resolves it.

    Hermes loads the profile ``.env`` over the unit environment, and a non-empty environment value wins
    over ``dashboard.basic_auth`` in ``config.yaml``. A plaintext environment password replaces any hash.
    """
    from plugins.dashboard_auth.basic import hash_password
    profile=Path(profile)
    path=profile/'config.yaml'
    value=YAML(typ='safe').load(_private_bytes(path))
    configured=value.get('dashboard',{}).get('basic_auth',{}) if isinstance(value,dict) else {}
    if not isinstance(configured,dict):configured={}
    layers=[_environment_file(profile/'.env')] if (profile/'.env').exists() else []
    layers.append(_unit_login(unit or dashboard_unit_environment))
    def environment(name):
        return next((layer[name].strip() for layer in layers if isinstance(layer.get(name),str) and layer[name].strip()),'')
    def configuration(key):
        return configured[key].strip() if isinstance(configured.get(key),str) else ''
    username=environment(LOGIN_VARIABLES['username']) or configuration('username')
    plaintext=environment(LOGIN_VARIABLES['password'])
    password_hash=(hash_password(plaintext) if plaintext else environment(LOGIN_VARIABLES['password_hash'])
        or configuration('password_hash') or (hash_password(configuration('password')) if configuration('password') else ''))
    if not username or not password_hash:
        raise ReleaseRejected('Complete removal currently requires a password-authenticated dashboard recovery owner')
    return {'username':username,'password_hash':password_hash}


def authenticate(profile, username, password, owner):
    from plugins.dashboard_auth.basic import BasicAuthProvider
    settings=basic_settings(profile)
    provider=BasicAuthProvider(username=settings['username'],password_hash=settings['password_hash'],
        secret=secrets.token_bytes(32),ttl_seconds=60)
    session=provider.complete_password_login(username=username,password=password)
    account='dashboard:'+session.provider+':'+session.user_id
    if account!=owner:raise PermissionError('The authenticated dashboard account does not own this removal')
    return account


def main():
    import argparse
    from . import memory_workflow
    from .removal_state import retained
    parser=argparse.ArgumentParser(description='Authenticate and resume or roll back the reviewed LifeOS removal')
    parser.add_argument('profile',type=Path)
    parser.add_argument('identifier')
    parser.add_argument('action',choices=('recover','rollback'))
    parser.add_argument('signature',help='Use the exact removal review signature from the saved receipt')
    args=parser.parse_args()
    try:
        source,configuration,job,plan=retained(args.profile)
        if job.name!=args.identifier or plan['signature']!=args.signature:
            raise ReleaseRejected('Use the exact profile, operation, and removal signature')
        print('This action changes software only. It retains current Hermes memory and native data.')
        username=input('Dashboard username: ')
        password=getpass.getpass('Dashboard password: ')
        owner=authenticate(args.profile,username,password,plan['owner'])
        del password
        result=memory_workflow.admit(args.profile,args.identifier,args.action,args.signature,
            owner=owner,launch=memory_workflow.launch)
        print('The authenticated removal recovery starts. Operation: '+result['identifier'])
    except Exception:
        print('Removal recovery refuses the current review, credentials, or artifacts.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
