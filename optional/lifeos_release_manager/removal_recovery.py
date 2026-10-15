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


def basic_settings(profile):
    from .release_programs import fingerprint
    path=Path(profile)/'config.yaml'
    identity=fingerprint(path)
    if identity is None or identity['type']!='file' or identity['mode'] & 0o077 or path.stat().st_size>1024*1024:
        raise ReleaseRejected('Standalone recovery requires the private current dashboard configuration')
    value=YAML(typ='safe').load(path.read_bytes())
    if fingerprint(path)!=identity:raise ReleaseRejected('The current dashboard configuration changes during authentication')
    settings=value.get('dashboard',{}).get('basic_auth',{}) if isinstance(value,dict) else {}
    if (not isinstance(settings,dict) or not isinstance(settings.get('username'),str)
            or not settings['username'] or not isinstance(settings.get('password_hash'),str) or not settings['password_hash']):
        raise ReleaseRejected('Complete removal currently requires a password-authenticated dashboard recovery owner')
    return settings


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
