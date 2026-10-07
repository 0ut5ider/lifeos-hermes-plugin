# Release rehearsal on the disposable guest and the full suite

Date: 2026-10-06. This unit runs the complete page workflow once, without manual steps, on the plugin at `9f91457`. It also runs the complete local test suite at the same commit. Production on `.212` stays unchanged.

## Guest workflow

The guest CT `100` starts from the snapshot `services-659246a`: stock Hermes `758ad514`, Bun 1.3.14, and the gateway and dashboard user services. The normal Hermes installer replaces the plugin with `9f91457`. [rehearsal.sh](rehearsal.sh) then calls the authenticated page routes in order. [guest/steps.txt](guest/steps.txt) records each step with its time.

| Step | Result |
| --- | --- |
| Prepare, apply, and finalize LifeOS; prepare and apply the Hermes patch | HTTP 200 each; host patch `applied` |
| Dashboard restart and status | LifeOS `installed`, hooks `patched_hooks_present`, no restart notice |
| Turn | "I'm LifeOS, your AI assistant." |
| Owner claim and fresh store for Adrian and Cerebo | Claim HTTP 200; store `review` with 0 active facts after about 20 seconds |
| Select the store | `applied`; turn: "I'm Cerebo, and you're Adrian" |
| Return | `applied`; turn: "I'm LifeOS, your DA on this system." |
| Prepare and apply a LifeOS update | `applied` without a baseline review; turn `READY` |
| Restore | `rolled_back` after the turn; VersionDrift 0 changes; turn `READY`; gateway active |

The whole workflow takes about 5.5 minutes.

## Full suite

[run-full.sh](run-full.sh) runs every `tests/test_*.py` module with the native, Hermes, fresh-source, and preparation repositories set. [full-suite-summary.txt](full-suite-summary.txt) records 2,052 tests in 2,668 seconds with 3 errors and 67 skipped tests:

1. `test_lifeos_installation` failed only in the full suite, because earlier tests leave real Hermes modules loaded. The next commit isolates the test.
2. `test_fresh_store` failed in a native `DeployCore` nested `bun install` for `LIFEOS/PULSE/Observability`: `Fail extracting tarball for "next"`. The same test passes alone. The guest's first page apply on 2026-10-06 failed in the same step. The cause is not known. A `/tmp` experiment produced the same message with `EDQUOT`, but this run used a home cache with free space, so quota does not explain it.
3. `test_ownership_setup` failed when the fixture's synthetic gateway unit timed out during start. It passes on repeat runs, before and after the ownership recovery change.

## Limits

- One rehearsal run.
- The guest has no Discord, no Pulse unit, and no enabled ownership.
- The skipped tests were not reviewed in this unit.
