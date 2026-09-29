# Permanent command allowlist and LifeOS policy

Date: 2026-09-28. Fixture: pinned Hermes and LifeOS source on the isolated `.212` account.

The installed native Safety hook denied an exact Bash command in LifeOS settings. Hermes still approved that command when its profile `command_allowlist` contained the same command text. The failing integration assertion was `assertFalse(permanent_denial["approved"])`; the actual value was true. The approval path returned from `_command_matches_permanent_allowlist()` before it called the plugin command policy hook.

The test fork now asks the plugin before it applies an exact permanent allowlist entry. The plugin deny blocks the command. Hermes hardline and user-deny checks still run first. The host unit test and the real installed Safety hook integration test pass. The prepared source check applies this as the seventeenth Hermes patch against the pinned base. The plugin suite passes 302 tests, with 55 optional tests skipped.

This result covers a manually configured exact command allowlist entry. It does not prove that every approval saved through Hermes's `Always` prompt follows the same path, or that a prepared batch decision and an off or yolo approval mode recheck changed LifeOS policy. Those remain separate permission cases in the parity plan. A paired Claude Code and Hermes action with complete approval traces remains open.
