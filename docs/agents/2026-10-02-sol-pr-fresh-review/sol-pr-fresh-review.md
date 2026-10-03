# Fresh pull request review

Date: 2026-10-02

Reviewer role: Independent code and integration reviewer

Question: Does the accumulated implementation in pull request 1 have actionable defects in supported or implemented behavior?

Model: GPT-6.1-Sol, high reasoning effort

Reviewed revision: `85c09023235fb358af18516b67bd5d012b2578ab`

Base revision: `648fe30a5c5f40551c9a3d73f0d80f527dbd7412` (`origin/main`, also the pull request base)

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

Pull request: <https://github.com/0ut5ider/lifeos-hermes-plugin/pull/1>

## Recommendation

Request changes. Two actionable findings survive reproduction. The restore finding blocks the advertised recovery behavior for an interrupted supported action. The source-label finding affects enabled owner review responses, including configurations that disable memory ownership and external sharing.

The reviewer did not modify implementation, tests, branches, services, installed systems, or GitHub. All new artifacts are in this review directory. All probe data is synthetic. The reviewer did not access the real shared memory store, private production data, authentication secrets, memory tools, or journal tools.

## Findings

### P1: Persist restore intent before stopping the gateway

Primary location: `lifeos_hook_bridge/update_transaction.py:309`. Related locations: `update_transaction.py:315`, `update_transaction.py:331`, `lifeos_hook_bridge/dashboard/plugin_api.py:535`, `plugin_api.py:640`, and `plugin_api.py:659`.

`restore_update` stops the gateway before it writes `state = restoring` to the durable transaction manifest. The new post-stop validation occurs in this interval. Process death after a successful stop leaves the manifest in `applied` state. The worker status remains `restoring`.

The dashboard detects the dead worker and reports `interrupted`. Its restore handler requires the dashboard state to be `applied`. Its recovery handler requires the transaction state to be `stopped`, `swapped`, `restoring`, or `rollback_failed`. Neither handler accepts this combination. The direct recovery function also rejects `applied`.

This ordering differs from the base implementation, which wrote the restoring state before it called `stop`.

#### Failing scenario

1. The owner applies a LifeOS update.
2. The owner requests restore of that applied update.
3. The restore worker stops the gateway.
4. The worker receives `SIGKILL` before it writes the restoring manifest.
5. The owner opens update status and tries restore or recovery.

The gateway remains stopped at the simulated service boundary. Both supported dashboard actions return HTTP 409. A manual service or status repair is required. The probe does not establish data loss.

#### Reproduction and output

Run from the repository with the safe environment in [the command manifest](raw/commands-revision.json):

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-pr-fresh-review/raw/probe-restore-stop-window.py
```

The probe applies an update to disposable directories. A real child process calls `restore_update`. Its stop callback records a synthetic stopped-service marker and kills that child. The probe then calls the actual dashboard status, restore, and recovery functions. It substitutes only the systemd liveness boundary. It never stops a real service.

Observed results from [the full output](raw/probe-restore-stop-window.txt):

```text
child_exit: -9
service_boundary_stopped: true
transaction_state: applied
dashboard_status.state: interrupted
dashboard_status.transaction_state: applied
restore: 409, There is no applied LifeOS update to restore
recover: 409, There is no interrupted LifeOS swap to recover
direct_recovery_refusal: Update snapshot does not need interrupted recovery
installed_owned_hook: owned-v2
profile_soul: selected soul
```

The primary reviewer independently ran this probe and reproduced the results in [its verification output](raw/primary-probe-restore-stop-window.txt).

#### Minimal suggested fix

Write a durable restore-stop intent before calling `stop`. Keep the post-stop user-data and profile checks. Define a safe recovery action for that intent. If post-stop validation fails, restart the selected installation and restore a coherent durable state. Do not permit a general recovery of any applied snapshot without current user-data and profile checks.

Add a process-death regression at the stop boundary. Confirm that the dashboard offers a valid recovery action and that the action restarts a consistent installation.

### P2: Apply source-label admission to adoption, canonical responses, and owner search

Primary location: `lifeos_hook_bridge/memory_canonical.py:49`. Related locations: `memory_canonical.py:60`, `memory_canonical.py:62`, `lifeos_hook_bridge/memory_adoption.py:109`, `memory_adoption.py:112`, and `lifeos_hook_bridge/memory_access.py:642`.

Adoption validates note bodies as generic native items. It does not validate the actual source filename. Canonical rendering compares the returned body with the declared body. It does not apply native private-source validation to the path. Owner search also returns the recorded `source.path` without source-label admission.

Canonical metadata filtering checks retired claims against raw labels. It does not normalize separators as the existing admission function does at `lifeos_hook_bridge/memory_sources.py:99`. A forgotten label encoded with underscores can pass this check.

These gaps share one cause: the paths and derived labels enter responses without the complete source admission policy.

#### Failing scenarios and activation conditions

The first probe creates a synthetic Knowledge note with a safe title and body. The filename contains `<private>SYNTHETIC_PRIVATE_FILENAME_MARKER`. The actual native `validate_source_batch` rejects that label. Adoption nevertheless commits one fact. Canonical output then includes the marker in `files` and `provenance.path`. The Knowledge response includes the marker in its note slug.

A separate probe uses the real owner account binding with `ownership_enabled = false` and `sharing_enabled = false`. Its owner adoption method commits the note. Both `knowledge_response` and explicit owner `lifeos_memory_search` return the private filename marker. This demonstrates an enabled owner review path. It does not depend on enabling future automatic memory ownership or external sharing.

The third probe forgets the claim `Synthetic retired canonical label`. It then adopts a safe-body note named `Synthetic_retired_canonical_label.md`. Native filtering excludes the normalized label. Canonical and Knowledge responses still return the filename and slug.

The required precondition is an adopted or registered source with an excluded label in its filename and otherwise admitted content. The probes invoke actual owner and native methods. They do not exercise an authenticated HTTP login or browser session.

#### Reproduction and output

Run each probe from the repository with the safe environment in [the command manifest](raw/commands-revision.json):

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-pr-fresh-review/raw/probe-canonical-label.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-pr-fresh-review/raw/probe-owner-label-response.py
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-pr-fresh-review/raw/probe-retired-canonical-label.py
```

Observed results:

```text
Native private-label validation: accepted false
Adoption: status committed, facts_adopted 1, excluded_sources 0
Canonical files and provenance.path: contain the private filename marker
Knowledge: status 200, slug contains the private filename marker
Owner configuration: ownership_enabled false, sharing_enabled false
Owner Knowledge private-marker check: true
Owner explicit search private-marker check: true
Forgotten-label normalized admission: excluded true
Retired-label canonical/Knowledge response check: true
```

Full outputs: [canonical label](raw/probe-canonical-label.txt), [owner response](raw/probe-owner-label-response.txt), and [retired label](raw/probe-retired-canonical-label.txt).

The primary reviewer independently reproduced all three probes. Its outputs are saved beside the reviewer outputs with the `primary-probe-` prefix.

#### Impact and limits

Excluded source labels enter owner review responses and the governed native canonical response. A filename can itself contain a private or retired claim. Filtering its body does not remove that claim from its path or slug.

The review does not demonstrate delivery to a model request, another user, or an external client. External sharing remains disabled on acceptance installations. This finding does not claim an unauthorized cross-account read. It concerns the admission policy for response text that the implementation already returns.

#### Minimal suggested fix

Validate the full declared source, including its actual path and metadata, before adoption and canonical rendering. Apply consistent separator normalization before retired-label checks. Apply the same rule to explicit search provenance labels. Reject the source or omit the excluded label according to one defined policy. Do not return the raw path after validation rejects that path.

Add regression cases for a private filename and a forgotten filename encoded with underscores. Cover owner Knowledge and explicit owner search with ownership and sharing disabled.

## Review method and scope

The reviewer read the coding-rules skill and its JavaScript reference. The reviewer identified changed runtime code, distributed patches, scripts, and meaningful tests before reading the previous integrated report. [The changed-file inventory](raw/changed-files.txt) records that selection.

The initial source assessment covered plugin registration, capability advertisement, middleware event paths, and native memory boundaries. It identified separate owner review operations and feature-gated automatic memory ownership and sharing. The reviewer then traced transaction and response paths before comparing prior findings and release claims.

The accumulated review covered these areas:

- Plugin registration, bridge setup, provider registration, Claude adapters, and supported Hermes middleware paths.
- Governed memory service, Remote Procedure Call and Model Context Protocol boundaries, account binding, grants, current scope checks, and native access.
- Context construction, retained history, model-call checks, request and delivery admission, and selected native consumers.
- Source adoption, canonical rendering, Knowledge rendering, wiki corpus admission, retired claims, owner proposals, preferences, and administration.
- Install preparation, mount snapshots, update and restore transactions, recovery admission, worker state, and installation locking.
- Dashboard update and memory flows, the compiled dashboard logic, and its focused interface tests.
- Development recording, event capture, redaction, recorder overlay setup, bootstrap, and recorder tests.
- Distributed source patch identity and the required middleware, plugin events, turn gates, native MemoryAccess, and Cortex integration paths.

The reviewer then compared the implementation with the previous integrated report and the final readiness evidence. The six prior integrated findings appear closed in the current code. The two findings above are separate remaining defects.

All 19 current patch hashes match the prepared source manifest. Both copies of every patch match. [The hash results](raw/patch-hashes.json) preserve measured bytes and expected values.

## Verification results

The reviewer used public prepared sources and a private synthetic home. `TMPDIR` stayed inside that home for successful runs. The setup provided real Bun and created `.cache`. It did not copy workstation project settings.

| Selection | Result | Evidence |
| --- | --- | --- |
| Installation locks, mount/update/worker transactions, owner administration, prompts, source review | 114 selected; 113 passed; 1 environmental skip; exit 0 | [transactions](raw/transactions.txt) |
| Provider, service, native memory, model calls, runtime, history, authorization, context, Knowledge query, wiki corpus | 141 passed; no skips; exit 0 | [memory boundaries](raw/memory-boundaries.txt) |
| TaskGovernance capability transaction plus adoption, canonical, staging, Knowledge rendering | 62 passed; no skips; exit 0 | [source neighbors](raw/source-neighbors.txt) |
| Development recorder | 32 passed; no skips; exit 0 | [recorder](raw/recorder.txt) |
| Dashboard and memory dashboard Node tests | 12 passed; no skips; exit 0 | [dashboard](raw/dashboard.txt) |
| Standalone restore stop-window probe | Reproduced finding P1 | [probe](raw/probe-restore-stop-window.txt) |
| Three standalone source-label probes | Reproduced finding P2 | [probe files](raw/) |

The initial transaction skip lacked `LIFEOS_TASK_HOOK_PATH`. The supplemental selection sets that variable to the prepared native hook and passes the skipped case. No failing check was silently skipped or weakened.

The full accumulated `git diff --check` exits 2. It reports whitespace in archived evidence, documentation, and patch-file text. The raw output and a path summary are saved in [diff check](raw/diff-check.txt) and [its summary](raw/diff-check-summary.json). This check does not establish a correctness defect.

[The command and revision manifest](raw/commands-revision.json) gives exact test selections, probe commands, environment paths, exit codes, and source identities. [The fixture setup history](raw/fixture-setup-history.txt) records unsuccessful setup attempts. The original stdout from two failed fixture attempts was overwritten during setup. Successful outputs are preserved in full.

## Limits and unreviewed surfaces

The reviewer did not rerun the complete Python suite. The targeted selections cover concrete risks and the adjacent source paths. The reviewer did not verify all archived evidence independently.

The review did not perform a live deployment, stop a live gateway, use a real model account, send a real external message, or run an external client. Model and systemd boundaries in tests are isolated boundaries. These results are not live end-to-end delivery evidence.

The reviewer did not line-review every diagnostics helper, every upstream native reader, or every hook patch. The review does not establish paired side-effect equivalence for all 74 hooks. Existing targeted tests and hash checks do not prove complete behavior equivalence.

Established-profile import and removal, complete native reader inventory, restricted delivery and lifecycle acceptance, schema rollback compatibility, and full hook parity remain explicit future gates. The reviewer does not reject the pull request for honestly leaving those gates incomplete and inactive.

Automatic memory ownership and external sharing remain disabled on acceptance installs. Implemented experimental paths were still assessed where possible. Missing planned functionality is not listed as a defect.

## Items for Adrian's review

The restore journal ordering requires correction before merge. A service stop must have a durable recovery state. The fix must preserve the newer post-stop data-preservation checks.

The source-label policy must cover every response field that carries source identity. The proven exposure is owner and native response text. Downstream model and external-client exposure remains unproven.

No change outside this review directory needs rollback. The primary reviewer has independently reproduced both findings and will verify the final test claims before reporting them.
