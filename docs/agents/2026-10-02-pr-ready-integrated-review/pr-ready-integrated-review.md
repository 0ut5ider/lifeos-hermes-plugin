# Integrated review of PR 1

Date: 2026-10-02
Role: Independent integrated code reviewer
Question: Can the complete LifeOS plugin PR leave draft while future memory ownership and full hook parity remain explicitly unavailable?
Model: GPT-6.1-Sol
Reasoning effort: high

## Revision and scope

Initial revision: `dc27ac4fea322c05c030438f8416be7763ded547`, branch `feature/lifeos-memory`, compared with `origin/main`.

Final correction revision: `36727e508c0795868045968d86cdace0c88f9d35`. The primary commits the six review corrections and the provider wording correction in this revision.

The primary changes the shared worktree during this review. This report distinguishes initial findings from independently verified corrections. `raw/reviewed-worktree.diff` and `raw/reviewed-source-hashes.json` identify the source exercised during correction verification. `raw/final-reviewed-revision.txt` identifies the committed correction revision. Tests recorded before this commit remain worktree verification; this metadata update does not label them as a new test run against the committed revision.

The review covers the complete PR scope. Source inspection centers on the active plugin registration, Hermes provider and required middleware integration, native memory service and caller policy, dashboard authentication and actions, managed mounting, installation, LifeOS and Hermes update and restore paths, recoverable publication, bundled native read boundaries, development capture, and current release claims. It includes source preparation and neighboring bridge safety tests, rather than only the latest restore changes.

No production machine, external memory store, or deployed service is changed. All executable tests use disposable local profiles and the supplied prepared source fixtures. Systemd update launch is replaced in HTTP probes. Native mounting, authentication sessions, file transactions, process-death tests, and patch preparation use real local implementations.

## Findings

### R1, P1: Other-origin requests can finalize and queue updates

Initial code: `lifeos_hook_bridge/dashboard/plugin_api.py`, installation finalization and update creation routes.

A verified owner session accepts `Origin: http://testserver:8081` on the `http://testserver` dashboard. Real native finalization returns HTTP 200, mounts the profile, and creates the baseline. Update creation then returns HTTP 200, publishes an update job, issues an owner grant, and calls the detached launcher.

The Hermes authentication middleware validates the cookie session but does not enforce HTTP Origin. SameSite=Lax does not protect against a different origin on the same site, such as another port. A hostile sibling page can submit these no-body POST actions. CORS prevents reading an unauthorized response, but it does not prevent the action.

Reproduction and exact results: `raw/probe-update-origin.py` and `raw/probe-update-origin.txt`.

The primary adds an Origin dependency for plugin mutation routes and the fixed request guard for installation actions. Independent replay now returns HTTP 403 for finalization and update, creates no baseline or grant, and does not call the launcher. See `raw/probe-update-origin-closure.txt`. The corrected administrative route suite also exercises rejected bodies and query overrides. This finding is closed in the reviewed worktree.

### R2, P2: The existing recovery test calls the changed endpoint incorrectly

Initial code: `tests/test_dashboard_api.py:313`, `test_reports_interrupted_update_and_launches_recovery`.

The endpoint becomes asynchronous and requires a Request, but this test still calls it synchronously without one. The integrated 188-case selection fails with:

```text
TypeError: recover_lifeos_update() missing 1 required positional argument: 'request'
Ran 188 tests in 163.662s
FAILED (errors=1)
```

The primary updates the caller to execute the synchronous recovery helper. The corrected 58-case administrative, dashboard, and transaction suite passes without skips or resource warnings. This finding is closed in the reviewed worktree.

### R3, P2: Version restore blocks the dashboard event loop

Initial code: `restore_lifeos_update` in `lifeos_hook_bridge/dashboard/plugin_api.py`.

The asynchronous route awaits its request guard and then calls synchronous status inspection, restore validation, authorization, and service launch directly. A harmless launcher subprocess that sleeps for 0.8 seconds delays an unrelated asynchronous dashboard GET by 0.8224 seconds.

Reproduction: `raw/probe-restore-scheduling.py` and `raw/probe-restore-scheduling.txt`.

The primary moves the synchronous restore sequence into `run_in_threadpool`, matching recovery. Independent replay serves the concurrent request in 0.0022 seconds while the same 0.8-second launch runs. See `raw/probe-restore-scheduling-closure.py` and its output. This finding is closed in the reviewed worktree.

### R4, P2: Prepared memory UI advertises unavailable agent operations

Initial code: `lifeos_hook_bridge/dashboard/dist/index.js`, current-fact review instructions.

The panel renders for prepared profiles with ownership disabled and says to ask the agent to correct or forget a fact. `LifeOSMemoryProvider.is_available()` requires ownership_enabled=true. The intended installation therefore cannot use that advertised route.

The primary conditions the instruction on enabled ownership and explicitly states that activation is unavailable in this version. The corrected UI selection passes all 12 cases. This finding is closed in the reviewed worktree.

The related provider wording advisory is also closed in `36727e5`. Source inspection verifies that `LifeOSMemoryProvider.unavailable_reason()` now states that ownership cannot be activated in this release. It separately names the tested host-extension requirement for experimental ownership profiles. The wording no longer directs users to an unavailable setup action. The exact committed change is retained in `raw/provider-wording-closure.diff`; this prose correction does not require another runtime test.

### R5, P2: Current installation and update guides contradict the acceptance record

`docs/update-policy.md` describes eight Hermes patch groups and nine LifeOS patches, while the installer declares nine and ten. It also says an authenticated page click remains untested. `docs/installation-workflow.md` repeats the old Hermes count and says fresh LifeOS installation has no live browser acceptance. README retains a broad browser-click limitation beside its newer acceptance description.

The completed bounded browser acceptance record establishes fresh LifeOS setup and same-revision update behavior. It does not establish every Hermes-extension browser action or full hook parity. Update the current operational claims and preserve the specific limits. Historical dated evidence need not be rewritten as though those checks happened earlier.

The primary updates README, the current installation workflow, and the update policy. The revised text names nine Hermes and ten LifeOS patch groups, links completed fresh-install browser acceptance, and retains the specific unverified Hermes-extension and full-parity limits. Source inspection closes this finding.

### R6, P1: Concurrent authenticated updates can own the same installation

Current active route: `apply_lifeos_update` in `lifeos_hook_bridge/dashboard/plugin_api.py`.

The route reads the latest job state, then creates and launches a job without serializing that sequence. Two requests that both observe state none can each queue an update for the same installation. The independent probe synchronizes the two real status reads before either publishes a job. Both requests return HTTP 200. Two jobs, two owner grants, and two launcher calls result.

Reproduction: `raw/probe-concurrent-updates.py` and `raw/probe-concurrent-updates.txt`.

The update workers and directory-swap transaction do not hold an installation operation lock across the complete update, restore, or recovery. Mount publication has a lock, but it occurs after the LifeOS directory swap. That lock cannot serialize the competing code transactions. The probe proves competing admission; it does not claim to reproduce data loss or live systemd interleaving.

The documentation excludes concurrent launches from one correction's acceptance scope. The active dashboard still permits the unsafe operation. Serialize update admission and complete worker ownership across apply, restore, and recovery. A second owner request must receive a conflict before it issues another grant or launches another worker. The primary adds a real private flock to LifeOS admission and detached update workers. Seven lock, concurrent-admission, and neighboring worker tests pass independently. A remaining cross-action gap is reproduced: holding the installation lock does not prevent an authenticated Hermes restore from changing its real manifest to restoring and calling its launcher. The active Hermes apply and restore admission and detached host worker need the same lock. See `raw/probe-host-lock.py` and `raw/probe-host-lock.txt`. The primary extends the shared lock to Hermes patch admission and its detached worker. Independent replay now returns HTTP 409, leaves the manifest applied, and never reaches the launcher while the profile lock is held. See `raw/probe-host-lock-closure.txt`. The final 77-case correction suite passes without skips or resource warnings and includes source preparation from the supplied repositories. Source inspection and this replay close the cross-action gap and R6.

## External user-data restore change

The primary adds `user_data_links` to the applied update manifest. The record binds each external root link's text, resolved target, device, and inode. Restore validates both installed and prior-tree aliases against that record. External owner data stays in its current directory; embedded data remains subject to strict content digests.

This addresses the supplied acceptance failure correctly. Copying an earlier external data snapshot would risk reviving a retired fact. Restoring only code while keeping current external data preserves later facts and appended native audit records.

Independent transaction verification passes all 15 cases without skips. Tests include changed external audit data, a deleted old fact, a current added fact, substituted targets and links, a changed prior-tree link, strict embedded-data refusal, filesystem-separated profile archives, and process-death recovery. The administrative dashboard fixture now creates the corresponding prior tree and link metadata. No additional material defect is found in this reviewed change. Same-account concurrent filesystem replacement and power-loss durability remain outside this evidence.

## Verification results

| Selection | Result | Evidence |
| --- | --- | --- |
| Initial installation, memory admission, restore, dashboard, provider, and regeneration selection | 188 cases, one test caller error | `raw/python-tests.txt` |
| Neighboring bridge, lifecycle, patch bundle, install, update, child adapter, native task, HTTP, source review, and memory dashboard selection | 275 cases, one optional preparation skip | `raw/neighbor-tests.txt` |
| Development recorder | 32 cases pass | `raw/recorder-tests.txt` |
| Initial dashboard JavaScript | 11 cases pass | `raw/ui-tests.txt` |
| Current external-data transaction suite | 15 cases pass, no skips | `raw/link-restore-tests.txt` |
| Corrected administrative dashboard, dashboard API, and update transaction selection | 58 cases pass, no skips | `raw/closure-tests.txt` |
| Corrected dashboard JavaScript | 12 cases pass | `raw/closure-ui-tests.txt` |
| Real complete source preparation | One case passes | `raw/preparation-test.txt` |
| New installation lock, concurrent update admission, and update worker | Seven cases pass | `raw/lock-tests.txt` |
| Final corrections including real source preparation and both host and LifeOS transaction paths | 77 cases pass, no skips or resource warnings | `raw/final-closure-tests.txt` |
| Actual agent turns, model calls, history repair, store ownership, and background review | 49 substantive cases pass; one source-input fixture failure | `raw/lifecycle-tests.txt` |

The skipped source-preparation case receives its actual repository fixtures in the lifecycle selection. The supplied repositories already use feature/lifeos-hook-parity as their default branch; cloning that branch then creating it again fails. A first disposable normalization attempt also hits `/tmp` disk quota during checkout. Both failures remain in the raw evidence. A bare repository retry fails the script's working-tree requirement. The final rerun uses private shared working-tree repositories without a checkout. Their default HEAD names the upstream base, and the test uses a filesystem-backed TMPDIR. This real complete patch-preparation case passes in 4.665 seconds. Its output is `raw/preparation-test.txt`.

`git diff --check` passes at the review checkpoint. The hook inventory reports 74 tracked native registrations. These checks do not establish semantic side-effect parity.

## Recommendation and limits

All six actionable findings and the related provider wording advisory are closed in correction commit `36727e5`. The final independent correction gate passes. This integrated review finds no remaining material defect in the inspected and exercised implementation. The PR can be ready for review with its future capabilities explicitly unavailable, subject to the primary's final full regression and current-revision acceptance gates. The corrections do not require memory activation or a claim of full production parity. Memory activation, existing-memory import, established-installation trials and removal, restricted audience delivery, retained-session reconstruction, complete source coverage, schema rollback compatibility, full PULSE interfaces, and complete hook side-effect parity remain separate future acceptance work.

This review does not rerun the entire historical 600-case memory regression, real production services, remote SSH or Docker fixtures, every native registration's paired side effects, a live browser, or private-model network calls. Test fixtures intercept some model and service boundaries. Passing tests at those boundaries do not establish final model delivery or production operational parity. The primary owns the full PR readiness gate and live acceptance evidence.


## Primary acceptance update after this review

The primary reports successful browser apply and restore on the isolated `.212` acceptance installation, including preservation of a synthetic audit append after update. This reviewer does not rerun those live actions and does not present them as independently verified results.

The primary also reports that two configuration-watcher test failures result from runner TMPDIR outside the synthetic HOME. Ancestor settings discovery reaches workstation settings in that layout. Both cases pass with TMPDIR under the synthetic HOME. This reviewer does not independently reproduce that runner diagnosis.

The complete final regression is still ongoing at this metadata update. This report makes no claim that the full gate passes. The primary remains responsible for its final result and current-revision live acceptance record.
