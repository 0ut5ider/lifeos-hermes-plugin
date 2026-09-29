# ABOUTME: Exposes LifeOS inference and integrity checks through Hermes plugin commands.
# ABOUTME: Runs each command inside the selected Hermes runtime and profile.

from __future__ import annotations

import argparse

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


def register_commands(ctx) -> None:
    ctx.register_cli_command(
        "lifeos-infer", help="Run a LifeOS child call with the selected Hermes provider.",
        setup_fn=claude_direct.configure_arguments, handler_fn=claude_direct.main,
    )
    ctx.register_cli_command(
        "lifeos-probe", help="Check or measure LifeOS model routing.",
        setup_fn=configure_probe, handler_fn=run_probe,
    )
