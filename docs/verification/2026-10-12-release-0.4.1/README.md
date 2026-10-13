# LifeOS 0.4.1 qualification

The patch candidate corrects an actual public bootstrap failure.
Stock Hermes v0.21.7 checks `args.version` before it dispatches plugin commands.
The release manager also stores its exact release choice in that field.
Both separated and equals-form `--version` therefore print the Hermes version instead of preparing a release.
The fix uses `args.release_version` and preserves the external option spelling.
It adds no Hermes or LifeOS patch group and changes no dependency lock.

The real parent/subparser regression fails before correction and all seven command tests pass after correction.
The initial additional test invocation names a nonexistent dashboard module. Its loader error remains recorded.
The corrected focused checks use the actual module name.
The public root CLI failure and its output remain in the 0.4.0 evidence folder.
The published 0.4.0 assets stay immutable. The default latest path is verified separately.
The daily guest remains on exact 0.3.1. No personal data is imported or reset.
The corrected complete 0.4.1 package must pass review and qualification before publication or daily promotion.
