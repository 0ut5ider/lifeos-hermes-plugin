Date: 2026-10-13
Role: Independent complete PR18 correctness reviewer
Question: Does the complete product diff preserve owner authorization, source integrity, lifecycle, recovery, configuration, UI behavior, and qualification honesty before merge?
Model: Inherited parent Codex GPT-6 model. The exact harness model identifier is not exposed in this review context.

Reviewed head: `3463a95bb42d6068ef5b8218aed4d7bb1ec9c246`.
PR base: `958d122a491ddead7c19a5f215494f0422c4b5d6`.
PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/18
Branch: `feature/release-ui-install-tests`.

## Result

Two actionable admission defects remain. The existing selected release and service controls pass, but they do not cover these boundaries. No product source, guest, production host, existing untracked artifact, published asset, certificate, or agent setting was changed during this review.

### P1: Bind the first-install dashboard service to the selected profile before draining it

Location: `optional/lifeos_release_manager/release_services.py:81-88`, particularly the admission conditions at lines 84-86. The filtering behavior is at lines 124-130. The worker uses the admitted service in `release_worker.py:395-399`.

Trigger: The selected account has a fixed `hermes-dashboard.service` using the account's regular `~/.local/bin/hermes` launcher and the account home as its working directory. Its actual dashboard process has `HERMES_HOME` pointing to another physical profile in the same account. A fresh preparation targets a different profile.

`fresh_preview()` checks the executable path, unit-file location, drop-ins, working directory through `ProfileServices`, and selected-profile foreground writers. It never checks the profile identity of the dashboard unit's `MainPID`. `check_dashboard_writers()` explicitly skips dashboards whose discovered profile differs from the requested profile. Consequently, a foreign dashboard is not a refusal: it disappears from the writer check while its fixed unit is admitted as the service to stop and restart.

Impact: A first installation can stop another profile's dashboard, replace the shared account launcher, and restart that foreign dashboard against the new runtime. The intended selected-profile binding is not established before service interruption. A similar revalidation gap exists if the running process identity changes between preparation and drain while the unit definition remains unchanged: the recorded service signature excludes the process profile identity, and the service barrier verifies files, working directories, and control groups rather than the actual Hermes profile.

Reproduction: `boundary_probes.py` starts a real synthetic Python process through a file named `hermes`, with the native-recognized `dashboard` command and an explicit foreign `HERMES_HOME`. Native `_hermes_home_for_pid()` reads the actual process identity and returns the foreign profile. The real `fresh_preview()` returns its signature for the requested profile rather than refusing. `boundary-probes.json` records both physical profiles, the actual PID, and the accepted signature.

Verification limit: The process and native procfs profile discovery are real. The systemd unit-inspection boundary is synthetic. This is a component admission reproduction, not actual installed-service or browser acceptance. No service was stopped by this probe. The separate selected suite does run the project's actual temporary user-service controls, but those controls do not reproduce this foreign-environment case.

Minimal correction: Before admission, bind an active dashboard `MainPID` to the exact requested physical Hermes profile and a recognized dashboard or serve invocation. Fail closed when that identity cannot be obtained. Verify the unit's effective profile selection for an inactive dashboard. Revalidate the same profile binding immediately before drain and on restart; a file hash and matching account launcher alone do not prove the current backend's profile. Add a focused real-process regression and an actual isolated service trial with a deliberately foreign `HERMES_HOME` before any stop occurs.

### P2: Serialize synchronous CLI preparation with dashboard preparation

Location: `optional/lifeos_release_manager/release_preparation.py:62-65`, with the independent synchronous path in `cli.py:99-106`.

Trigger: `hermes lifeos-release prepare`, including the conversational preparation path, is still downloading or staging a release. A concurrent authenticated client requests `/prepare` for the same profile.

The synchronous path publishes its live process identity, so `status()` correctly returns `preparing`. It does not retain `preparation.lock`. `queue()` obtains that lock and scans operation states, but the refusal set omits `preparing`. The dashboard path therefore admits another preparation while the synchronous path is active. Another synchronous CLI invocation can similarly bypass the dashboard's lease and active/recovery admission checks.

Impact: Duplicate complete-package downloads, dependency generations, and native-reference builds can run concurrently under the same profile, despite the documented duplicate-preparation refusal. Each creates a durable operation and a plan against the same active installation. The frontend's disabled buttons do not protect direct API requests or simultaneous chat/CLI requests. This probe does not show unauthorized program publication or data loss.

Reproduction: `boundary_probes.py` calls the real `cli.prepare()` with a bounded catalog download boundary. That boundary records the live `preparing` status, invokes the real `queue()`, and uses Python tracing to stop immediately before its second `Popen()`. The probe records `queue_reaches_child_launch=true` and `created_jobs=2`. Its first operation remains `preparing`. No release download or second child launch occurs after the trace boundary.

Minimal correction: Use one private preparation admission lease for both entry points. A synchronous CLI preparation must acquire and retain it until completion. The already admitted detached child must reuse the inherited lease without reacquiring its own lock. Apply the active/recovery refusal rules to synchronous admission too. Include a regression that pauses a real synchronous preparation before download and verifies that another CLI or API preparation refuses before creating another job or spawning a child.

## Complete review scope

I inspected the complete base-to-head diff for all 35 files outside review and qualification evidence directories, saved as `product-diff.patch`. This includes the two copies of the native child-routing test patch, all version declarations, README and changelog behavior claims, the new frontend and backend routes, release preparation, archive and extracted-source validation, retained worker validation, program publication, first-install service generation, separate service journals, fresh recovery, and baseline preservation. I also read the unchanged operation, initialization, catalog, and program-transaction context needed to assess the modified paths.

Owner authorization remains routed through actual native dashboard sessions. The selected HTTP controls exercise anonymous and forged denial, foreign account denial, current owner revocation, foreign-origin mutations, and bounded input refusal. The prepare route passes selections rather than authority or a caller-supplied profile. Active installation still requires a separate review and apply action.

The extracted main manifest is compared with the certificate-bound regular archive before candidate imports. Both native source manifests are hashed against that authenticated main manifest. Retained worker files are checked before admission. The selected controls exercise coordinated program/map changes, altered native source metadata, missing and changed archives, symlinks, FIFOs, duplicate manifests, and changed retained workers. I found no additional actionable archive or retained-worker integrity defect in those changed paths.

The fresh service barrier uses `.lifeos-installation-services` and the candidate bridge namespace during recovery. Existing installations retain the three-role `.lifeos-services` behavior. Program transactions skip publication of unchanged files, preserve their inode and timestamp, and refuse later edits during recovery. Unchanged native updates preserve the baseline's original `created_at`, so repeated preparation produces the same baseline bytes.

First-install caught-error handling only resumes the admitted program phase after native initialization is complete, verifies the runtime and service definitions, and leaves the operation requiring recovery. Native and user destinations are retained rather than erased. The README accurately states that an abrupt manager-directory swap can require the retained qualified worker through an operator recovery path. Public CLI recovery is not claimed for every possible swap point.

YAML configuration staging uses real round-trip parsing and block formatting for native mount headers. The selected controls verify preserved model choices, plugin effort settings, unrelated plugin selection, and original configuration bytes. Generated unit tests use the actual systemd parser and refuse unsupported physical path characters before generation.

The UI controls prepare a complete package for each update intent, poll operation state, expose operation identifiers, retain separate review/apply actions, and block active/recovery phases. The three Node controls use a synthetic SDK and are component contracts. They are not browser acceptance.

## Qualification and publication evidence

The tracked verification README, PROGRESS.json, and the combined public acceptance receipt accurately distinguish synthetic prerelease qualification from daily production qualification. The two published archives and certificates remain immutable checkpoints. Their initial pending public-action field is not rewritten; the separate combined acceptance asset records the later public passes.

The recorded complete archive-bound integration gate passes 661 tests on rc.1. Its file map contains 21,085 regular files. The recorded official native gate passes 716 tests in 38 files through `scripts/run_tests.sh`. The rc.2 package is recorded as an exact version-only derivative of rc.1. I did not rerun either complete gate and do not describe them as fresh tests performed by this reviewer.

The combined receipt records public fresh install, both numerical update actions, numerical rollback, and Hermes conversational preparation followed by owner installation. `production_qualified` remains false. The default public GitHub URL bootstrap replay is explicitly `PENDING_PR18_MERGE`; the native web form has no revision selector. This declared dependency is not an unreported successful gate or a defect created by this review.

The artifact-verification script independently hashes the two archives, checks certificate receipt hashes and all 21 combined acceptance hashes, recomputes the exact archive derivative predicate and file-map digest, and validates a fresh task-owned rc.1 extraction. All checks pass. The 21,085 archived regular files match before and after the isolated controls, with no generated file additions in that extraction. Its complete measurements are in `artifact-verification.json`.

## Tests and exact commands

All commands below run from `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.

The focused integration command is:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning -m unittest -v \
  test_release_catalog test_release_programs test_release_stage \
  test_release_manager_cli test_release_operation test_release_configuration \
  test_release_native_config test_release_dashboard test_release_preparation \
  test_release_services test_profile_services
```

Result: exit 0; 99 tests reported in 30.081 seconds; 96 execute and 3 skip for absent optional qualification fixtures. Those skips are the sealed fresh-recovery lease test, the prepared fresh candidate bridge test, and historical fresh-review HTTP refusal. Standard verbose unittest output appears in `focused-tests.stderr`; stdout is empty. No ResourceWarning or unexpected diagnostic occurs. The actual temporary service fixtures stop and remove their own isolated units after testing.

The exact two-boundary reproduction command is:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-final-review-1/boundary_probes.py
```

Result: exit 0; both defect probes reproduce; `boundary-probes.stderr` is empty. `boundary-probes.json` contains the measurements and explicit component limits.

The frontend command is:

```sh
node --test tests/test_release_ui.cjs
```

Result: exit 0; all 3 tests pass; stderr is empty. `ui-tests.stdout` contains the complete TAP results.

The observational archive/evidence command is:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-final-review-1/verify_artifacts.py
```

This command launches only the isolated fresh lease regression and six artifact-binding controls after the read-only verification and fresh extraction. Result: exit 0; all 7 tests pass in 46.078 seconds with no skips. This closes the sealed fresh-recovery lease skip from the first selected run. The two historical prepared-operation fixture cases remain unexecuted in this review. `artifact-tests.stdout`, `artifact-tests.stderr`, and `artifact-verification.json` record the complete result. No native pytest command is used.

## Raw artifacts and verification limits

`inspected-file-hashes.json` contains SHA-256 hashes for 48 inspected product, context, and evidence files. `reviewed-state.json` records the exact base and head and an empty tracked working-tree status. `product-diff.patch` preserves the complete inspected non-evidence diff. The two observational scripts, their raw outputs, suite logs, boundary measurements, and archive verification output are in this directory.

I did not inspect private model/dashboard credential JSON or personal memory records. I did not call memory or journal tools. I did not access `.252`, `.253`, `.249`, or the removed `.250` SSH fixture. I did not run complete native or integration gates, deploy a package, change publication, or implement corrections. Existing historical untracked files remain in place.

The primary reviewer should reproduce the two probes, add failing regressions, correct admission, and verify an actual isolated foreign-profile service trial before merge. Any new release code must qualify as a new candidate rather than replacing the published rc.1 or rc.2 assets. The post-merge default GitHub bootstrap and daily deployment gates retain their stated scopes.
