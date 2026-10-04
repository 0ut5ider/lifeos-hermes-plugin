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
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--create', metavar='DIRECTORY', help='Create a private native data snapshot.')
    actions.add_argument('--inspect', metavar='DIRECTORY', help='Verify a native data snapshot without restoring it.')
    actions.add_argument('--recover', metavar='DIRECTORY', help='Recover a native snapshot into a separate tree without selecting ownership.')
    parser.add_argument('--signature', help='Require the recorded manifest signature during inspection or recovery.')
    parser.add_argument('--destination', metavar='DIRECTORY', help='Create the separate native recovery tree at this path.')


def run_backup(args: argparse.Namespace) -> int:
    from hermes_constants import get_hermes_home
    from .installation_lock import installation_lock
    from .memory_access import NativeMemory
    from .memory_backup import create, inspect
    from .memory_backup_recovery import recover
    from .memory_preferences import MemoryPreferences
    from .memory_service import MemoryConfiguration
    configuration = MemoryConfiguration(get_hermes_home() / 'lifeos-memory.json')
    if args.recover and (not args.signature or not args.destination):
        print(json.dumps({'status': 'rejected', 'message': 'Native recovery requires --signature and --destination.'}), file=sys.stderr)
        return 1
    if args.destination and not args.recover:
        print(json.dumps({'status': 'rejected', 'message': '--destination applies to native recovery.'}), file=sys.stderr)
        return 1
    try:
        if args.create and args.signature:
            raise ValueError('Manifest signatures apply to inspection')
        with installation_lock(configuration.path.parent), configuration._lock():
            config = configuration.load()
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
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired):
        print(json.dumps({'status': 'rejected', 'message':
                         'Native backup is unavailable under the selected profile. Check its configuration, store, permissions, and destination.'}),
              file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


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
        'lifeos-backup', help='Create or verify a private native LifeOS data backup.',
        setup_fn=configure_backup, handler_fn=run_backup,
    )
