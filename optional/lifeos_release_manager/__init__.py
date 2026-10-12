# ABOUTME: Registers complete integration release management without changing the active bridge.
# ABOUTME: Keeps release preparation available on stock Hermes and accepted installations.
from pathlib import Path


def register(ctx):
    from .cli import configure, run
    ctx.register_cli_command('lifeos-release', help='Prepare, approve, and recover complete LifeOS integration releases.',
        setup_fn=configure, handler_fn=run)
    ctx.register_skill('lifeos-release', Path(__file__).parent / 'skills/lifeos-release/SKILL.md',
        'Install and update the complete LifeOS integration through a qualified Hermes release.')
