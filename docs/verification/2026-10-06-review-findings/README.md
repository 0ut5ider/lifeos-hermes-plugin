# Remaining review findings

Date: 2026-10-06. This unit corrects the open findings from the [memory module review](../../agents/2026-10-05-pr3-memory-modules-review/pr3-memory-modules-review.md) and the [runtime review](../../agents/2026-10-05-pr3-runtime-review/pr3-runtime-review.md). Each correction starts with a test that fails on the earlier code. Production on `.212` stays unchanged.

| Finding | Commit | Correction |
| --- | --- | --- |
| Managed HTTP mode lost when both marker files disappear | `510cbd5` | With ownership enabled, prompt admission refuses the turn and names the mount repair. No second marker. |
| State paths wrong for named profiles | `71719f1` | `account_home()` maps `~/.hermes/profiles/<name>` to the account home for fresh stores, import staging, and the default LifeOS home. The mount accepts only the exact recorded workspace. |
| Unbounded nested proposal fields | `008ff89` | Every nested proposal field has a type check and a bound before the native worker runs. |
| A repeat migration replaces the earlier backup | `73267aa` | A backup whose fixed name already holds other bytes goes to a digest-named file. The journal plan covers it. Two earlier tests asserted the overwrite; they now assert the kept copy. |
| The Bun wrapper checks only the literal `install` | `8712b51` | The wrapper finds the subcommand after global options. `install` and `i` must use the frozen form; dependency-changing subcommands are refused. |
| Ownership recovery stops services forever after a completed rollback | `3bf5d42` | Recovery skips a rollback that the ownership journal already records, and resumes the services. |

## Test runs

- Freshness, access, and related memory groups: 212 tests pass with `LIFEOS_FRESHNESS_CONTROL_SOURCE` set. Without that variable, nine tests error on the missing variable, before and after these changes.
- Fresh store, fresh store worker, and native dependencies with the current 11-patch candidate: 33 tests pass, including full native installs through the wrapper.
- Ownership setup and ownership: 27 tests pass with real user services.
- Proposal argument and memory service groups: 147 tests pass.

## Limits

- A tool that starts Bun through `process.execPath` bypasses the PATH wrapper.
- The marker guard covers turns through the bridge. Native Pulse and command-line tools outside the bridge are not covered.
- Correction, forget, and proposal calls still have no grant check inside their transaction, as the earlier review unit records.
