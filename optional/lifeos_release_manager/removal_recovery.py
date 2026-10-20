# ABOUTME: Authenticates standalone software recovery with the actual Hermes dashboard password provider.
# ABOUTME: Issues the same exact owner workflow grant after the active manager has been removed.
import getpass
from pathlib import Path
import re
import secrets
import sys
import types

if not __package__:
    package=types.ModuleType('lifeos_removal_recovery_manager')
    package.__path__=[str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__]=package
    __package__=package.__name__

from .release_catalog import ReleaseRejected


SCRYPT_HASH=re.compile(r'scrypt\$[1-9][0-9]*\$[1-9][0-9]*\$[1-9][0-9]*\$[A-Za-z0-9+/]+={0,2}\$[A-Za-z0-9+/]+={0,2}')


def recovery_login(value, owner):
    """Return the dashboard password login that authorizes standalone recovery for ``owner``.

    Removal preparation records the login of the running dashboard password provider, the one that
    authenticated the owner, so recovery never re-reads configuration that the removal can change.
    """
    if (not isinstance(value,dict) or set(value)!={'username','password_hash'}
            or not isinstance(value['username'],str) or not value['username'] or len(value['username'])>256
            or not isinstance(value['password_hash'],str) or SCRYPT_HASH.fullmatch(value['password_hash']) is None
            or owner!='dashboard:basic:'+value['username']):
        raise ReleaseRejected('Complete removal currently requires a password-authenticated dashboard recovery owner')
    return value


def authenticate(login, username, password, owner):
    from plugins.dashboard_auth.basic import BasicAuthProvider
    provider=BasicAuthProvider(username=login['username'],password_hash=login['password_hash'],
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
        owner=authenticate(recovery_login(plan.get('recovery_login'),plan['owner']),username,password,plan['owner'])
        del password
        result=memory_workflow.admit(args.profile,args.identifier,args.action,args.signature,
            owner=owner,launch=memory_workflow.launch)
        print('The authenticated removal recovery starts. Operation: '+result['identifier'])
    except Exception:
        print('Removal recovery refuses the current review, credentials, or artifacts.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
