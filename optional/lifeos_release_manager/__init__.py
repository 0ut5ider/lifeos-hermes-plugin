# ABOUTME: Registers complete integration release management without changing the active bridge.
# ABOUTME: Keeps release preparation available on stock Hermes and accepted installations.
def register(ctx):
    from .cli import configure, run
    ctx.register_cli_command('lifeos-release', help='Prepare, approve, and recover complete LifeOS integration releases.',
        setup_fn=configure, handler_fn=run)
