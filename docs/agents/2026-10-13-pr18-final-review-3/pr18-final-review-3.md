Date: 2026-10-13
Agent role: Independent complete PR18 correctness reviewer, third pass
Question: Does the complete PR18 product diff, including admission, effective-environment, bundled-launcher, and rc.3 corrections, contain any remaining actionable correctness defect?
Model: Codex GPT-6, inherited parent model. The exact harness model identifier is not exposed in this review context.

Final reviewed commit: `b9d353cdf1cca571194d1f60c269efdc97880fe5`.
PR base: `958d122a491ddead7c19a5f215494f0422c4b5d6`.
Correction base: `3463a95bb42d6068ef5b8218aed4d7bb1ec9c246`.
PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/18
Branch: `feature/release-ui-install-tests`.
Final correction diff SHA-256: `e13fb7a16e064af6b6666ddce9856db23b6980b67d865087b49d6e5478b84935`.
Final complete product diff SHA-256: `9d1c064bfd259bbfc9a862b4ea9bd25c930dd2e2209f6f9fdac47614dd285899`.
Final tracked working tree: clean.

## Result

No actionable code-review findings remain in the complete inspected product diff at the final commit. The original foreign-dashboard profile defect, overlapping preparation defect, and literal-percent environment regression are corrected. A supported bundled-launcher recognition defect discovered during this round is also corrected and independently verified before this report closes.

This is source and component review clearance. The new rc.3 candidate still requires its own complete-package qualification. The immutable rc.1 and rc.2 archives do not contain these final corrections. The default-public-GitHub web bootstrap remains a declared post-merge gate. Daily production qualification remains outside these synthetic prerelease checks.

## Closed correctness findings

The foreign-profile service correction validates the active process's native Hermes profile, account UID, recognized command, and stable process start stamp. It validates the unit's effective physical HERMES_HOME, configured dashboard or serve invocation, explicit profile overrides, and sticky-profile selection. Environment files refuse. The current fresh-service subclass applies that validation inside every inherited service inspection and includes the binding in the definition digest, so admission, drain, recovery, empty-process checks, and restart revalidate it. It does not rely solely on the initial preview or the launcher filename.

Synchronous CLI preparation and UI preparation retain the same private preparation lease. Admission checks pending installation and recovery before job creation, and checks live legacy preparation identity. The detached child uses its already admitted job and inherited descriptor. It does not reacquire the lease it holds. Real file, flock, trace-boundary, and process-liveness regressions pass. Stale preparation permits a retry; an active preparation refuses duplication.

The environment parser now compares the effective HERMES_HOME directly. Systemd has already expanded unit-file specifiers. My independent actual inactive-unit probe now accepts the exact physical path containing literal consecutive percent signs. The project's actual inactive-unit regression also verifies that a declared environment file refuses. The parser accepts an absent empty EnvironmentFiles property because the real manager omits it, while Environment itself remains required through direct lookup. A nonempty EnvironmentFiles property still refuses.

During this round, the primary's actual guest preflight identified a supported-launcher refusal. The pinned bundled launcher executes Python with `-P -c` and the exact source:

```python
import os, site, sys; sys.argv[0]='hermes'; site.addsitedir(os.environ['HERMES_SITE']); from hermes_cli.main import main; sys.exit(main())
```

The native generic command matcher returns None for this official shape. I independently reproduced that result from the safe actual guest argv receipt and checked the upstream launcher generator. The new active PID check would therefore reject a correct bundled dashboard, including a dashboard restarted onto the qualified assembled runtime.

The final correction adds a narrow `dashboard_command()` adapter for that exact pinned in-process bootstrap. It is shared by the PID guard, configured command check, and foreground writer scan. It does not accept arbitrary inline source. My independent replay of the actual guest argv now returns dashboard. Adding `; pass` to the source returns None. The real-child controls verify matching and foreign profiles under the official bundle shape, and verify that unrelated inline source does not claim a bundled dashboard. All pass. `bundled-launcher.json` preserves the earlier native-matcher refusal, while `bundled-adapter.json` preserves the corrected behavior.

## Complete product assessment

I reviewed the complete product diff from the PR base to the final commit, including the initial 35-file product scope and all subsequent corrections. The final correction commit changes 12 tracked files: admission and service code, their regressions, README prerequisites, five version declarations, and the changelog. `final-complete-product-diff.patch` and `final-working-diff.patch` preserve those exact inputs. `final-inspected-file-hashes.json` records 56 inspected product, context, native reference, and evidence file hashes.

Owner authorization remains based on native authenticated dashboard sessions and current installation-owner policy. Anonymous, forged, foreign-account, revoked-owner, foreign-origin, malformed, and oversized request controls pass. Prepare accepts a bounded selection rather than caller-supplied profile or authority. Review and apply remain separate. Native memory mounting still requires its bound owner grant where ownership is active.

The source-validation changes authenticate the extracted main manifest against the certificate-bound regular archive before candidate imports. Native source manifests match the authenticated main map. Exact bridge, manager, and dependency maps refuse coordinated or unrecorded changes. Retained worker files are checked before admission and launch. The selected tamper and boundary controls pass. I found no additional actionable integrity defect in those changed paths.

First installation retains a dashboard-only service journal in `.lifeos-installation-services`, with the candidate bridge namespace and installation lease. Existing installation updates retain the three-service barrier in `.lifeos-services`. The independent local actual-service controls pass service drain, child-writer emptiness, restart, unchanged definition publication, later-definition refusal, alias refusal, retained state, and abrupt-exit recovery.

Program publication preserves unchanged file inodes and timestamps. Recovery and rollback refuse later program changes. Native initialization retains published user trees and preserves later user data rather than recreating it. Fresh caught-error handling only resumes the admitted program phase after recorded native initialization, verifies the runtime and service definitions, and leaves native mount completion as explicit recovery. The documented operator path remains necessary for some abrupt manager-directory swap points; the report does not claim public CLI recovery at every such point.

YAML staging preserves model and tier settings, unrelated plugin choices, and original active configuration bytes while preparing native block headers. Unchanged native updates preserve the original baseline creation time. Generated units pass the actual systemd parser. Unsupported physical paths refuse before service generation.

The three UI preparation actions still select the complete integration. Their owner review/apply separation, polling, visible operation identifier, package identity display, and active/recovery button blocking remain intact. The three Node SDK contract tests pass. They remain component tests, not browser acceptance.

The mechanical version changes update all five declarations to 0.4.2-rc.3. The changelog records the new admission and launcher corrections. Eight version controls pass. The existing rc.1 and rc.2 artifacts are preserved rather than rewritten.

## Actual guest component evidence

I read the primary-produced CT106 trial source and raw receipt. I did not access or mutate the guest myself. The trial uses the actual installed Hermes process, owner user systemd manager, procfs profile discovery, service control group, and drain/resume behavior. It does not claim a complete installer or browser replay.

The fixed main service passes preview. A temporary service then starts with a foreign profile while its unit definition remains unchanged. Drain refuses before creating a service journal, and the foreign service PID remains 5018. A matching temporary service drains and resumes, changing PID from 5030 to 5052 with the same definition. The primary's cleanup removes its task-owned units and synthetic profiles.

The main dashboard PID remains 4038. The main configuration and integration-release receipt hashes are identical before and after the trial. `guest-service-trial.stdout` preserves the before/after hashes and results, and its stderr is empty. Copies of the trial source and raw output are included here with their exact inspected hashes.

This component evidence verifies the new service admission and revalidation against the actual bundled launcher. The default public GitHub URL installation of the new manager, followed by fresh complete-package browser acceptance, remains the declared post-merge replay gate.

## Qualification evidence and limits

The prior immutable rc.1 archive remains qualified against the recorded 661-test complete archive-bound integration gate and 716-test official native gate across 38 files. The rc.2 archive remains the exact version-only derivative previously verified. Their certificate receipt hashes and all 21 combined public acceptance hashes match in this review. The initial certificate pending-public-action checkpoint remains distinct from the subsequent immutable acceptance receipt.

I validated the retained task-owned rc.1 extraction against its certificate again. The current fresh-service controller uses the same candidate installation lease successfully in a tiny isolated profile. No new complete package was extracted. The six artifact-binding controls pass. I did not rerun the complete integration or native gates and do not attribute them to rc.3.

The original selected suite still skips three optional fixture cases: the fully prepared fresh candidate bridge, historical fresh-review HTTP refusal, and the sealed fresh-recovery lease test that performs another complete extraction. Prior rounds already executed that sealed lease control successfully. This round instead directly exercises the current controller with the retained candidate's real lease without another extraction. The two historical prepared-operation cases remain unexecuted by this reviewer.

The current final source changes require a new rc.3 complete-package build and qualification, and any published rc.3 claim must bind those new exact bytes. The primary owns that work. Stable release selection, default-branch web replay, and daily deployment remain governed by their existing explicit gates.

## Independent checks and exact commands

All commands run from `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`. Structured command metadata and complete outputs are retained here.

The complete selected suite before the narrow bundled-launcher adapter is:

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

Result: exit 0; 109 reported, 106 execute, 3 optional fixture skips, 29.937 seconds. This run does not cover the subsequent adapter. The affected service, preparation, and actual-local-service controls are independently repeated after that adapter:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning -m unittest -v \
  test_release_services test_release_preparation test_profile_services
```

Result: exit 0; all 38 pass, no skips, 20.410 seconds. This includes the new official-bundle matching/foreign controls and unrelated-inline negative control. Standard verbose reports are captured in stderr; no ResourceWarning or unexpected diagnostic occurs.

The independent actual effective-environment probe is:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-final-review-3/environment_probe.py
```

Result: exit 0; the actual inactive unit with a double-percent physical profile now returns accepted=true. Stderr is empty. No service process starts.

Retained source and evidence checks run through `review_retained.py` with the same Python/PYTHONPATH settings. Result: exit 0; the retained package validates, the candidate lease/controller check passes, both certificate receipt sets match, and all 21 acceptance hashes match. The script extracts no new package. `retained-verification.json` preserves its results.

The artifact controls use the same interpreter with `PYTHONPATH=.:tests:docs/verification/2026-10-13-release-ui-install:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream` and `-B -W error::ResourceWarning -m unittest -v test_qualification_artifacts`. All 6 pass, no skips, in 0.011 seconds.

The rc.3 version controls use the normal selected-suite environment and `-B -W error::ResourceWarning -m unittest -v test_release_version`. All 8 pass, no skips, in 2.091 seconds.

`node --test tests/test_release_ui.cjs` passes all 3 SDK component contracts. Stderr is empty. No direct native pytest invocation is used.

## Scope of actions

I wrote only this round's authorized review artifacts and operated isolated local test fixtures. Previous review reports remain unchanged. I did not edit product code, initialize or commit a repository, push, merge, change published assets or certificates, change agent settings, access private model/dashboard credential JSON, inspect personal memory records, or call memory/journal tools. I did not access or change `.252`, `.253`, or `.249`. The actual CT106 component results are explicitly attributed to the primary.

The remaining review focus is the new rc.3 package's exact qualification and the post-merge public web bootstrap. These are declared acceptance work, not unresolved source-review findings.
