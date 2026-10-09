# ABOUTME: Exposes LifeOS inference and integrity checks through Hermes plugin commands.
# ABOUTME: Runs each command inside the selected Hermes runtime and profile.

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from . import carrier_probe
from .bin import claude_direct


def configure_probe(parser: argparse.ArgumentParser) -> None:
    checks = parser.add_mutually_exclusive_group(required=True)
    checks.add_argument("--check", action="store_true")
    checks.add_argument("--run", action="store_true")
    checks.add_argument("--check-main-rung", metavar="TIER")


def run_probe(args: argparse.Namespace) -> int:
    if args.check_main_rung:
        return carrier_probe.main(["--check-main-rung", args.check_main_rung])
    return carrier_probe.main(["--run" if args.run else "--check"])


def configure_backup(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--scope', choices=('native', 'profile'), default='native',
                        help='Select native data or the selected Hermes profile together with native data.')
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--create', metavar='DIRECTORY', help='Create a private snapshot for the selected scope.')
    actions.add_argument('--inspect', metavar='DIRECTORY', help='Verify a snapshot without restoring it.')
    actions.add_argument('--recover', metavar='DIRECTORY', help='Recover a snapshot into a separate tree without selecting ownership.')
    parser.add_argument('--signature', help='Require the recorded manifest signature during inspection or recovery.')
    parser.add_argument('--destination', metavar='DIRECTORY', help='Create the separate recovery tree at this path.')


def run_backup(args: argparse.Namespace) -> int:
    from hermes_constants import get_hermes_home
    from .installation_lock import installation_lock
    from .memory_access import NativeMemory
    from .memory_backup import create, inspect
    from .memory_backup_recovery import recover
    from .memory_preferences import MemoryPreferences
    from .memory_service import MemoryConfiguration
    from . import profile_backup
    from .profile_backup_recovery import recover as recover_profile
    configuration = MemoryConfiguration(get_hermes_home() / 'lifeos-memory.json')
    if args.recover and (not args.signature or not args.destination):
        print(json.dumps({'status': 'rejected', 'message': 'Recovery requires --signature and --destination.'}), file=sys.stderr)
        return 1
    if args.destination and not args.recover:
        print(json.dumps({'status': 'rejected', 'message': '--destination applies to recovery.'}), file=sys.stderr)
        return 1
    try:
        if args.create and args.signature:
            raise ValueError('Manifest signatures apply to inspection')
        if args.scope == 'profile' and (args.create or args.recover):
            if args.create:
                result = profile_backup.create(configuration, Path(args.create).expanduser())
            else:
                result = recover_profile(configuration, Path(args.recover).expanduser(), args.signature,
                                         Path(args.destination).expanduser())
        else:
            with installation_lock(configuration.path.parent), configuration._lock():
                config = configuration.load()
                if args.scope == 'profile':
                    manifest = profile_backup.inspect(configuration, Path(args.inspect).expanduser(), args.signature)
                    result = {'status': 'verified', 'profile_files': len(manifest['files']), 'created': manifest['created']}
                else:
                    memory = NativeMemory(Path(config['root']))
                    scope = MemoryPreferences._owner_scope(config)
                    if args.create:
                        result = create(memory, scope, Path(args.create).expanduser())
                    elif args.recover:
                        result = recover(memory, scope, Path(args.recover).expanduser(), args.signature, Path(args.destination).expanduser())
                    else:
                        manifest = inspect(memory, scope, Path(args.inspect).expanduser(), args.signature)
                        result = {'status': 'verified', 'files': len(manifest['files']),
                                  'schema': manifest['schema'], 'created': manifest['created']}
    except profile_backup.ProfileBackupTooLarge as error:
        print(json.dumps({'status': 'rejected', 'message': str(error)}), file=sys.stderr)
        return 1
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired):
        print(json.dumps({'status': 'rejected', 'message':
                         'The backup is unavailable under the selected profile. Check its configuration, store, permissions, and destination.'}),
              file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


def configure_owner_job(parser: argparse.ArgumentParser) -> None:
    from .memory_owner_jobs import JOBS
    parser.add_argument('job', choices=tuple(JOBS), help='Run one configured native owner job.')
    parser.add_argument('--configuration-revision', help='Require the initiating owner configuration revision.')


def run_owner_job(args: argparse.Namespace, read_setting) -> int:
    from hermes_constants import get_hermes_home
    from hermes_cli.inventory import load_picker_context
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from .memory_owner_jobs import OwnerJobs
    from .model_tiers import configured_model_map
    try:
        current = load_picker_context()
        provider = resolve_runtime_provider(requested=current.current_provider, target_model=current.current_model)
        route = {'provider': provider['provider'], 'model': current.current_model,
                 'base_url': provider['base_url'], 'api_mode': provider['api_mode']}
        mapping = configured_model_map(read_setting, current.current_provider, current.current_model)
        result = OwnerJobs(get_hermes_home() / 'lifeos-memory.json').run(args.job, route=route, mapping=mapping,
            expected_revision=getattr(args, 'configuration_revision', None))
    except (ValueError, OSError, RuntimeError, KeyError, sqlite3.Error, subprocess.TimeoutExpired):
        result = {'status': 'rejected', 'job': args.job,
                  'message': 'The native job needs current local owner permission, an admitted model route, and a managed store.'}
    print(json.dumps(result))
    return 0 if result['status'] == 'completed' else 1


def register_commands(ctx) -> None:
    ctx.register_cli_command(
        "lifeos-infer", help="Run a LifeOS child call with the selected Hermes provider.",
        setup_fn=claude_direct.configure_arguments, handler_fn=claude_direct.main,
    )
    ctx.register_cli_command(
        "lifeos-probe", help="Check or measure LifeOS model routing.",
        setup_fn=configure_probe, handler_fn=run_probe,
    )
    ctx.register_cli_command(
        'lifeos-backup', help='Create or verify private LifeOS data and selected-profile backups.',
        setup_fn=configure_backup, handler_fn=run_backup,
    )
    ctx.register_cli_command(
        'lifeos-job', help='Run a native background job with current local owner permission.',
        setup_fn=configure_owner_job, handler_fn=lambda args: run_owner_job(args, ctx.get_config),
    )
