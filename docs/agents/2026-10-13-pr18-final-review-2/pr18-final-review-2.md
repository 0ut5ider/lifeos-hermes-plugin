Date: 2026-10-13
Role: Independent complete PR18 correctness reviewer, second pass
Question: Do the complete product diff and the working-tree admission corrections resolve the first review without introducing another correctness defect?
Model: Codex GPT-6, inherited parent model. The exact harness model identifier is not exposed in this review context.

Committed head: `3463a95bb42d6068ef5b8218aed4d7bb1ec9c246`.
PR base: `958d122a491ddead7c19a5f215494f0422c4b5d6`.
PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/18
Branch: `feature/release-ui-install-tests`.
Working diff SHA-256: `de5f230bf62c9c8c75ace2ccfbd37ca5bc993b4bcca58bd4c85056659f229de2`.
Complete base-to-working-tree product diff SHA-256: `93bf6db97f21c974f167db6c33b4ceaec58642b7c408eefd44e91e3333dd8060`.

## Result

The original P1 foreign-dashboard admission defect and P2 overlapping-preparation defect are corrected in the inspected working tree. One new P2 parser regression remains. I found no additional actionable defect in the complete inspected product diff.

### P2: Do not decode percent specifiers from effective systemd environment values

Location: `optional/lifeos_release_manager/release_services.py:112`, with the resulting refusal at lines 114-116.

Trigger: A supported physical account or profile path contains two consecutive literal percent signs, such as `/tmp/account/literal%%name/.hermes`. `_service_paths()` explicitly accepts percent signs. Service generation correctly escapes each percent sign for the unit file. The new `dashboard_binding()` reads the effective `Environment` property from the actual systemd manager.

Systemd already expands unit-file percent specifiers before returning `Environment` through `systemctl show`. The new `.replace('%%', '%')` therefore changes actual literal characters in a valid physical path. It turns the effective `literal%%name` into `literal%name`, so the selected-profile comparison refuses a service that has the correct profile and dashboard invocation.

Impact: Fresh preparation and the inherited fresh-service inspection paths reject a supported service configuration. This is a functional refusal regression. The probe does not show unauthorized installation or data loss.

Measured reproduction: `environment_probe.py` creates one task-owned inactive user unit. It writes the profile environment with the existing `_quoted()` helper and obtains real `MainPID`, `ExecStart`, `Environment`, and `EnvironmentFiles` properties through `systemctl show`. The unit file contains `literal%%%%name`; the effective property correctly contains `literal%%name`. `_service_paths()` accepts the physical home, profile, and native path. Calling the real `dashboard_binding()` rejects the correct effective property with `The dashboard service requires an explicit selected profile and dashboard command`.

`environment-probe.json` records the exact unit text, requested physical profile, effective environment, `MainPID=0`, and refusal. Unlike the original round 1 foreign-profile probe, this experiment uses an actual systemd unit and actual effective properties. No service process starts. It remains a parser component experiment, not browser installation acceptance. The fixture removes only its own runtime unit link and temporary directory.

Minimal correction: Compare the already effective `Environment` value directly. Remove the redundant percent replacement. Add a regression using an actual inactive temporary unit with a literal double-percent physical profile path, and verify that a genuinely different profile still refuses.

The primary agent independently accepts this finding and plans the correction and third review. This reviewer does not change product code.

## Closure of the original findings

### Original P1: Foreign dashboard service profile and missing revalidation

`fresh_services()` now constructs a subclass of the qualified `ProfileServices` class. Its `_inspect()` calls the existing trusted service inspector, validates the dashboard binding, and incorporates that binding into the definition digest. The inherited preview, drain, empty-process verification, quiescence, recovery, and restart paths all call this inspector, so the profile check does not end at preparation.

For active processes, `dashboard_binding()` obtains the native Hermes profile, checks the process UID, checks its recognized dashboard or serve command, and compares the process start stamp before and after discovery. It refuses an unavailable identity or a different physical profile. For configuration, it checks a recognized dashboard or serve invocation, explicit physical `HERMES_HOME`, the absence of environment files, explicit profile flags, and sticky-profile selection. The README records the stricter explicit-profile prerequisite.

The new controls use actual synthetic processes and native procfs discovery with a labeled synthetic unit-inspection boundary. They verify active and inactive foreign-profile refusal, wrong configured invocation refusal, matching active and inactive admission, and reinspection after the configured profile changes. These controls pass independently in this review. The systemd environment parsing regression above does not reopen the foreign-profile authorization defect; it is an over-refusal introduced by the correction.

### Original P2: Synchronous CLI preparation bypasses the UI lease

The new `preparation_admission()` context manager owns the common private preparation lock and performs sibling-operation admission checks before job creation. Synchronous `cli.prepare()` retains this lease for its complete `_prepare()` call. The UI queue retains the same lease until its child inherits the descriptor. The admitted child passes its existing job and therefore does not reacquire the lock it already holds.

The status scan distinguishes a real live legacy preparation PID from stale or incomplete preparation state. It blocks queued application, active installation, recovery, rollback, and required recovery before creating a job. New regressions confirm the shared synchronous/UI lease, refusal under an already held lease, refusal during pending installation or recovery, and retry after an expired preparation. All pass independently.

## Complete product review

I rechecked the complete base-to-working-tree product diff, rather than only the latest admission patch. `complete-product-diff.patch` preserves that review input. The committed product scope remains the 35 files from the first review. The working corrections touch six tracked files: the README, CLI, preparation module, service module, and their two test files. `inspected-file-hashes.json` preserves 48 exact inspected file hashes, including the unchanged context and qualification evidence used to assess the product paths.

Owner authorization remains routed through native authenticated dashboard sessions, current owner policy, and separate review/apply actions. Request selections remain bounded and do not accept caller-supplied authority or profile destinations. The independent selected HTTP controls pass anonymous and forged denial, foreign-account denial, current revocation, foreign-origin denial, and malformed or oversized selection refusal.

The certificate-bound archive manifest comparison, authenticated native source-manifest hashes, exact bridge and manager maps, and retained-worker admission checks are unchanged by this correction. Their refusal controls pass. I found no new source-integrity defect in these paths.

The fresh dashboard-only barrier still uses the candidate namespace and `.lifeos-installation-services`; existing installations retain the three-service barrier. The new binding digest remains stable across a legitimate stop and restart because it binds profile and configured command, not an ephemeral PID. The actual temporary user-service suite passes unchanged publication, complete drain, restart, abrupt exit, retained state, alias refusal, and later definition-edit refusal. The percent parser reproduction also verifies the real manager's effective environment semantics.

Program publication still preserves the inode and timestamp of unchanged service files. Fresh failure handling retains native and user publication state, only resumes an admitted program phase, and reports required recovery rather than successful native mounting. Recovery and rollback refuse later program edits. The README retains the operator-recovery limit for an interruption that removes the installed manager directory.

YAML staging still preserves model choices, plugin effort settings, unrelated plugin configuration, and original active configuration bytes. The unchanged-native baseline preserves its creation time and produces consistent repeated preparation bytes. Generated service definitions still pass the real systemd parser, and unsupported path characters refuse before generation.

The three UI actions still prepare the complete package and retain separate owner review and installation. Polling, visible operation identifiers, and active/recovery button blocking remain unchanged. The Node contract tests pass. They use a synthetic SDK and remain component tests.

## Evidence scope and verification limits

The existing rc.1 and rc.2 archives and certificates are immutable historical qualification inputs. The first archive remains bound to the prior 661-test integration gate and 716-test official native gate. The second remains its verified version-only derivative. The new admission corrections are working-tree product changes and are not claimed to be present in those already published archives or tested by those historical complete gates.

The existing combined public acceptance hashes and certificate hashes were verified in round 1. Their inspected evidence file hashes remain unchanged in this review snapshot. I reran the six artifact-binding controls and the sealed fresh-recovery lease control using the retained task-owned build fixture, rather than invoking the extraction script again. All seven pass. I did not rerun the complete archive-bound integration gate, complete native gate, or browser installation checks.

The primary agent reports that its additional CT106 temporary-service trial has not started at this report checkpoint. I do not claim a guest trial result. The planned actual component trial does not substitute for the declared post-merge fixed-unit fresh bootstrap replay. The native web form still lacks a revision selector, and default-public-URL replay remains pending merge. Production qualification remains false.

I read no private model/dashboard credential JSON or personal memory records. I used no memory or journal tools. I did not mutate a guest, production host, published asset, certificate, agent setting, existing untracked artifact, or product source. I did not push, merge, or commit. The primary agent owns fixes and guest acceptance.

## Tests and commands

All commands run from `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.

Selected release and actual temporary-service controls:

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

Result: exit 0; 108 tests reported in 29.466 seconds; 105 execute and 3 optional fixture cases skip. No ResourceWarning or unexpected diagnostic occurs. The suite uses actual temporary local user services and cleans its own units.

Actual environment regression reproduction:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-final-review-2/environment_probe.py
```

Result: exit 0; the parser defect reproduces against the actual inactive unit. The report records `accepted=false` and the matching effective physical environment. Stderr is empty.

Retained-fixture lease and artifact controls:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.:tests:docs/verification/2026-10-13-release-ui-install:/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream \
LIFEOS_QUALIFICATION_BUILD=docs/agents/2026-10-13-pr18-final-review-1/sealed-review-bg1aw0o2/build.json \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning -m unittest -v \
  test_release_operation.ReleaseOperationTests.test_fresh_recovery_keeps_one_lease_namespace_after_bridge_publication \
  test_qualification_artifacts
```

Result: exit 0; all 7 pass in 45.453 seconds with zero skips. The sealed lease test's own temporary fixture extracts and removes its isolated input as part of the existing test; the retained build/extraction remains unchanged. This covers the sealed lease case that skips in the first command. Two historical prepared-operation fixture cases remain unexecuted in this review.

UI command:

```sh
node --test tests/test_release_ui.cjs
```

Result: exit 0; all 3 pass; stderr is empty. No direct native pytest command is used.

## Raw artifacts

The report directory contains `working-diff.patch`, `complete-product-diff.patch`, exact inspected hashes, reviewed state and diff identities, structured command metadata, complete selected-suite and artifact-suite stdout/stderr, Node TAP output, the actual environment probe source, and its structured and raw measurements. The initial snapshot files preserve the state on which this finding is based.

The next review should verify the narrow effective-environment correction, its actual parser regression, and the additional service component evidence when available. Published test prereleases must retain their existing bytes and qualifications. Any corrected complete release requires its own candidate qualification.
