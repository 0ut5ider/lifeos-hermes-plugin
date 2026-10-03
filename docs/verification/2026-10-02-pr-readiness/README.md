# PR 1 readiness gate

Date: 2026-10-02

## Scope

This record supports moving PR 1 from draft to review. It does not authorize a merge or activate lasting-memory ownership.

The runtime correction revision is `36727e508c0795868045968d86cdace0c88f9d35`. Revision `567d9c9` updates one test assertion to check the current activation warning. It does not change deployed code. The final runner records the full tested revision and all 19 distributed patch hashes in `final-clean/source-identity.json`.

The supported revisions remain Hermes `758ad514eb0e800547e015edf05aa18f78b78d82` and LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Same-revision update acceptance does not establish compatibility with a newer upstream release.

## Corrections

1. Version restore retains current external LifeOS data. The snapshot binds the external directory links to their physical targets, devices, and inodes. Changed embedded data, replaced targets, and later profile changes still refuse restore.
2. Dashboard mutations reject requests from another origin. Fixed installation actions reject query parameters and request bodies.
3. Version restore runs its synchronous operations in the thread pool. The independent replay reduces the concurrent request delay from 822 milliseconds to 2.2 milliseconds.
4. LifeOS code transactions and Hermes patch workers share a private installation lock. Competing admission cannot create another job or owner grant. Process termination releases the lock.
5. The memory page and unavailable-provider message state that ownership activation is unavailable in this release.
6. Fresh source preparation accepts a source whose default branch already has the preparation branch name. The operation changes only the fresh output clone.

No Hermes or LifeOS patch changes in this correction unit. The independent [integrated review](../../agents/2026-10-02-pr-ready-integrated-review/pr-ready-integrated-review.md) closes all six findings. Its final correction selection passes 77 tests without skips or resource warnings. The primary also checks the actual unavailable-provider warning through the real host constructor.

## Live browser acceptance

The test uses the separate `lifeos-plugin-install-probe` account, UID 1007, and home `/home/lifeos-plugin-install-probe/acceptance-20261002`. It changes neither the existing `.212` account nor `.211` or `.213`.

The browser signs in through the real password form. T3 preview initialization reports unavailable, so the test uses Playwright. Credentials stay outside Git. The acceptance installation keeps lasting-memory ownership and external sharing disabled.

| Check | Result | Evidence |
| --- | --- | --- |
| Fixed installation request admission | Nine routes reject another origin and unsupported bodies, 18 expected rejections | `browser-baseline.json` |
| Reviewed VersionDrift renewal | The owner reviews one generated documentation timestamp change before renewal | `baseline-reviewed-diff.txt`, `browser-baseline.json` |
| Browser update | The actual detached worker applies the prepared source and restarts the gateway | `browser-update.json`, `browser-update-audit.txt` |
| Browser version restore | The prior program version returns and current external data remains | `browser-restore.json`, `browser-restore-post-update.txt` |
| Later external audit data | A post-update synthetic row increases the audit file from 321,501 to 321,597 bytes. Restore preserves all bytes and inode 221526129 | `audit-post-update-append.json`, `browser-restore.json` |
| Interrupted native mount | A real SIGKILL after the first published target leaves recovery required | `mount-process-kill.txt` |
| Browser mount recovery | The owner uses the visible recovery control. All eight targets regain their prior bytes and permissions | `browser-recover.json`, `mount-recovery-verification.json` |
| Running services | The dashboard, gateway, native routes, and loopback PULSE are active | `final-services.txt` |
| Deployed package | All 75 packaged files match the acceptance runtime | `deployed-package-verification.json` |

The first restore click receives a conflict while a successful update worker still holds the installation lock. The browser probe retries only that exact busy response. It does not retry validation or authorization errors. The first response remains in `browser-restore-busy.txt`.

The same-revision operator rehearsal in `operator-update.txt` issues a new job and action-bound grant. Later runs use the actual visible browser update and restore controls.

## Regression environment and failures

`run-final-regression.py` creates a private synthetic home, installs the prepared public native source, and runs the complete Python suite with resource warnings treated as errors. It also runs the separate development recorder and dashboard interface suites. Temporary projects stay inside the synthetic home. The runner never imports production memory.

The first exploratory run reports a source preparation disk quota error and a patch regeneration fixture mismatch. The corrected runner uses the `/home` filesystem and marks the ten new distributed test files in its private regeneration clone. It does not disable either test. The original output remains in `regression.txt`.

The first expanded run places temporary projects beside the synthetic home. Project discovery then reaches the workstation's ancestor settings. Two configuration watcher tests fail. Instrumentation identifies the incorrect root; both tests pass when temporary projects stay inside the synthetic home. The unchanged runtime behavior needs no correction. See `config-fixture-errors.txt`, `config-fixture-instrumentation.txt`, and `config-fixture-corrected.txt`.

A host test still expects the old unavailable-provider text. `provider-guidance-failure.txt` records that failure. The test now checks the explicit activation limit and retains its store, prompt, file, and tool assertions. All four host tests pass with the supplied native fixtures. A separate replay omits the native source and correctly finds an unavailable provider; its failed fixture output remains in `provider-native-fixture-missing.txt`.

The synthetic home initially omits its `.cache` directory. The actual memory SSH enrollment test cannot create its private fixture there. The runner now creates that directory with mode 0700. The localhost OpenSSH server still runs with strict permissions and the real forced command. The failure and corrected replay remain in `ssh-home-fixture-failure.txt` and `ssh-home-fixture-corrected.txt`.

The native tagged VersionDrift control initially receives a tag from the public repository root. That root has zero `hooks/` files and 97 `LifeOS/install/hooks/` files. The native control requires the installed layout. A private Git fixture now tags the prepared public hooks at that layout. The unchanged native hook emits one warning and suppresses its repeat. See `tagged-fixture-diagnosis.json` and `tagged-fixture-corrected.txt`.

The final complete outputs and command exits are in `final-clean/`. The prior expanded output remains in `final/`. The final result is recorded in `final-result.json`.

## Final results

The complete gate at `567d9c9193f8457596c271aa8deb4c64338e9419` passes.

| Selection | Result |
| --- | --- |
| Complete Python suite | 1,030 pass and 21 skip out of 1,051 selected cases; no failures, errors, or resource warnings |
| Private development recorder | 32 pass without skips |
| Dashboard interface | 12 pass without skips |
| Independent integrated correction review | 77 pass without skips; six findings closed |

The skip inventory in `final-result.json` names all 21 cases. Eight require Docker fixtures, eleven require remote workspace fixtures, one requires the browser-tool fixture, and one requires a private child-model configuration. The real localhost memory MCP enrollment test runs and passes; it is separate from remote workspace hook tests. The live acceptance browser also runs separately from the skipped browser-tool fixture.

The final evidence commit changes documentation and archived results only. The runtime package still matches the tested source. All three finite PR readiness gates pass: integrated review, current correction regression, and isolated browser acceptance. Complete memory activation and full hook parity remain separate gates.

## Limits that remain open

- Lasting-memory ownership activation and external sharing remain disabled.
- Remaining native readers and derivatives, restricted prompt and delivery paths, retained-session reconstruction, and recoverable ownership setup still need acceptance.
- Established-profile trials, reviewed memory import, removal, and return to Hermes remain planned.
- Schema rollback compatibility and newer upstream revisions remain unverified.
- Complete paired side effects for all 74 native registrations remain unclaimed. Environment-dependent remote and container tests cannot establish parity when skipped.
- The browser does not exercise the Hermes-extension install and restore buttons in this readiness unit.

These limits remain separate from readiness to review the implemented, inactive memory components and installation corrections.

## Changes outside Git and rollback

The deployment script changes only the separate acceptance plugin directory. It retains the previous runtime at `.local/state/pr-readiness-36727e5/plugin-before` under the acceptance home. Four dedicated user services restart. The program update and restore rehearsals use their transaction snapshots. The synthetic audit row is retained deliberately as test evidence.

To restore the prior plugin runtime, stop the four acceptance services, retain the current plugin directory, move `plugin-before` back to `.hermes/plugins/lifeos-hook-bridge`, then start the four services. Do not use a production account for this operation. The existing browser guide describes how to retire the entire acceptance environment.

Native PULSE remains bound to loopback port 8923. The narrow acceptance listeners use LAN ports 8921 and 8922. This correction changes no firewall rule or messaging credential.
