# Pinned LifeOS release gate

Date: 2026-09-29. Target: the disposable `lifeos-plugin-install-probe` account on `192.168.8.212`. Hermes base revision: `758ad514e`. LifeOS base revision: `5e2f2e8`. The tested Claude Code reference is 2.1.272. The private LAN model served both paired harnesses.

## Result

**The release gate is blocked.** The software test selections below pass, but the required 74 native and Hermes hook comparisons are incomplete. A follow-up Haiku model-alias control moved `TaskCreated.1.1` into the [paired ledger](../docs/parity/paired-live-coverage.json), which now records matching dispatch and output shape for 63 registrations and marks 11 as `not_observed`. This comparison does not prove identical handler side effects. No change was deployed to `.211` or `.213`.

| Check | Result | Scope |
| --- | --- | --- |
| LifeOS update transaction | Pass at the pinned revision | Direct and service-backed apply and restore, forced verifier failure with automatic rollback, detached API worker, 74 hook registrations, 13 dependency roots, 1,825 managed source files. Synthetic USER and MEMORY hashes stayed fixed. |
| Plugin Python suite | 376 tests, 65 skipped | Ran with the patched Hermes source first on `PYTHONPATH` and the plugin's managed dependency environment on the disposable account. Optional live cases were run separately where available. |
| Dashboard JavaScript tests | 3 passed | Local `node --test tests/test_dashboard_ui.cjs`. |
| Paired ledger tests | 7 passed | Local `python3 -m unittest discover -s tests -p 'test_paired*.py' -v`. |
| Real source preparation | 3 passed | Clean local clones received all 19 Hermes and 9 LifeOS patches in order. The prepared trees passed `git diff --check`. |
| Patched Hermes focused selection | 378 passed, 10 skipped, 5 subtests passed | Ran 22 modules touched by the Hermes patch bundle. |
| Live SSH and Docker gate | 19 passed, no selected skip | Disposable loopback SSH user and local `composer:2.8` container on `.212`. |

The first Hermes selection failed four desktop approval batch variants. An unmodified Hermes clone passed those variants. A thread dump showed that the second command waited for a new approval after the first command changed the working directory. Its pre-collected approval belonged to the old directory. The command context patch deliberately invalidates that approval. The bundled test now requires a fresh request and verifies that the second result is withheld until it is approved. The four variants and the complete focused selection pass. The revised patch also passed fresh source preparation.

The first source preparation attempt used Git worktrees. The preparation command requires a `.git` directory, so that fixture failed. Clean local clones passed without a product code change. A later Python suite attempt imported the managed Hermes package copy and lacked `tree_sitter`; the passing run selected the patched Hermes checkout and the managed plugin dependency environment. Its bundled patch copy was synchronized before that run.

## Update scope

The update candidate and active LifeOS installation had the same pinned revision. The rehearsal exercised staging, dependency installation, hook replacement, gateway stop and restart, verification, restore, and rollback. It did not exercise a changed upstream revision. The updater rejects unreviewed revisions and changes to generated `CLAUDE.template.md` or `settings.system.json` until their migrations are reviewed. An authenticated browser click was unavailable; the installed API launched and completed the worker.

## Unclosed parity cases

The eleven registrations without a paired native event are `PostToolUse.2.1` (`WebFetch`), `.3.1` (`WebSearch`), `.5.1` (`ToolSearch`), `.10.1` through `.10.7` (`MultiEdit`), and `StopFailure.1.1`. The LAN `WebFetch` control stopped before `PostToolUse` at Claude Code's private-address safety check. Direct HTTPS from the reference account to `example.com` could not connect, so a public fetch would require a network policy change. No external WebSearch request was made from the private test account. Claude Code's printed tool list on the local model had no `MultiEdit` or `ToolSearch`; a local 100-tool MCP server did not expose `ToolSearch`, even with longer tool descriptions under a Haiku identity. `TaskCreate` became available with a Haiku model identity routed through a temporary loopback proxy to the same private model. A loopback 400 response displayed an API error but did not fire native `StopFailure`; 401 and 503 retried beyond the capped probes. Hermes did fire its `StopFailure` handler for a terminal 401 error. These observations do not prove that the remaining registrations are impossible on every Claude Code build.

The 63 observed matches cover registration dispatch, status, and presence of output. They do not close all permission timing, approval transport, handler side effects, session history, or remote namespace cases in the [parity plan](../docs/parity-resolution-plan.md). The 19 live remote tests used SSH to the same host and one Docker image. Distinct SSH hosts, other container images and remote backends, a live gateway resume sequence, and several permission rule sources remain unverified. Release requires those cases to be tested or explicitly scoped out with evidence. The native reference must also expose the eleven missing events before a 74-outcome claim is possible.

## Probe cleanup

The disposable gateway was stopped and its test-only user service disabled and removed. The account's Hermes configuration was restored byte-for-byte from the pre-pairing backup after the task control. The Docker socket access control entry for the probe account, temporary SSH key, and temporary SSH user were removed. The Haiku alias proxy was stopped and its temporary credential copy removed. The account's existing systemd linger setting remains enabled. Raw traces and test logs remain private on `.212`; they are not in Git. The LifeOS installation and plugin remain in the disposable account for further tests.
