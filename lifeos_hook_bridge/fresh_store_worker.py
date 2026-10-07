# ABOUTME: Prepares one named fresh store in a process that outlives the dashboard request.
# ABOUTME: Records a failed outcome so the store listing separates failures from interruptions.

from __future__ import annotations

import argparse
import sys
import types
from pathlib import Path

if not __package__:
    package = types.ModuleType("lifeos_hook_bridge")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    __package__ = package.__name__

from .fresh_store import FreshStore, _identifier, _name
from .install_source import IncompatibleLifeOS
from .memory_access import MemoryUnavailable
from .memory_service import MemoryConfiguration


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a named fresh LifeOS store")
    for name in ("configuration", "candidate", "identifier", "principal-name", "assistant-name", "account"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        _identifier(args.identifier)
        _name(args.principal_name)
        _name(args.assistant_name)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    store = FreshStore(MemoryConfiguration(Path(args.configuration)))
    try:
        store.prepare(Path(args.candidate), principal_name=args.principal_name, assistant_name=args.assistant_name,
                      account=args.account, identifier=args.identifier)
        return 0
    except IncompatibleLifeOS:
        reason = "Fresh store preparation requires a verified native candidate"
    except PermissionError:
        reason = "An authenticated installation owner must prepare a fresh store"
    except (MemoryUnavailable, ValueError, RuntimeError, OSError) as error:
        reason = str(error)[:300] or "Fresh store preparation stopped"
    store.record_failure(args.identifier, principal_name=args.principal_name,
                         assistant_name=args.assistant_name, reason=reason)
    print(reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
