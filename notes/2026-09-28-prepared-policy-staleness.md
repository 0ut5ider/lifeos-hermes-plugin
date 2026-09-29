# Prepared desktop approval and changed policy

Date: 2026-09-28. Fixture: the isolated `.212` Hermes account with the installed native LifeOS Safety hook.

A prepared desktop terminal decision returned approval before the current LifeOS command policy hook ran. A regression with an exact LifeOS Bash deny and a matching prepared decision failed with `approved: true`. This test used a synthetic prepared slot to reach the real guard and installed hook. It did not run a complete desktop batch through the user interface.

The test fork now uses sequential terminal approvals when the active profile has a `pre_command_approval` callback. The policy hook runs once when each command reaches execution. If a prepared slot exists and a command policy hook becomes available before execution, the slot discards its cached decision and the guard runs again. This removes the stale decision path without invoking the hook twice in a normal plugin-enabled desktop batch. Desktop users with a command policy plugin will receive approval requests in execution order rather than as a pre-collected batch.

The real Safety hook guard regression, one focused desktop batch test, and the plugin suite pass. The plugin suite reports 302 tests with 55 optional skips. Four pre-existing desktop batch tests timed out in this test account, both before this patch and against an unmodified Hermes base, as recorded in [the replacement note](2026-09-28-permission-input-rewrites.md). They do not verify the new desktop policy path. A complete desktop user-interface sequence with a policy edit between two commands remains a parity gate.
