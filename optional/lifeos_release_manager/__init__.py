# ABOUTME: Registers LifeOS release management without changing the active bridge.
# ABOUTME: Keeps compatibility checks and release preparation available on stock Hermes.
from pathlib import Path


def register(ctx):
    from .cli import configure, run
    ctx.register_cli_command('lifeos-release', help='Check compatibility, then prepare, approve, and recover LifeOS releases for this Hermes installation.',
        setup_fn=configure, handler_fn=run)
    ctx.register_skill('lifeos-release', Path(__file__).parent / 'skills/lifeos-release/SKILL.md',
        'Install and update LifeOS in this Hermes installation through a qualified release.')
