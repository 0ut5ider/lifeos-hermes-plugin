# Memory proposal preferences review

Date: 2026-09-30
Role: Independent code reviewer
Question: Does the bounded owner proposal preferences unit preserve owner permissions, exact references, native outcomes, and truthful UI feedback without changing existing sharing or settings behavior?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

No material defect was found in the reviewed unit. All 18 focused tests passed. Additional probes verified real native decisions through FastAPI and UI feedback after a committed result followed by a failed refresh. This is a completed bounded review, not an activation approval or a complete memory design audit.

The reviewed baseline is d54c44ba3f187505d772d7705752b3e9a1c0abd4 plus the six uncommitted files listed below. Their hashes remained unchanged during review. No implementation code was edited and no commits were made. All records were disposable synthetic fixtures. No live servers, credentials, actual memories, or journal tools were accessed.

## Scope

- lifeos_hook_bridge/memory_preferences.py: owner scope and native capability status.
- lifeos_hook_bridge/memory_native.ts: proposal_capabilities action.
- lifeos_hook_bridge/dashboard/dist/index.js: proposal rendering, manual decisions, outcome reporting, and retained existing controls.
- tests/test_memory_preferences.py, tests/test_memory_dashboard.py, tests/test_memory_dashboard_ui.cjs.
- Existing dashboard/plugin_api.py and memory_service.py were read to check the actual request boundary and permission dispatch.

The native proposal state machine was already reviewed at the baseline. This review exercised that state machine through the new preferences surface without repeating the broader native inventory or host admission audit.

## Verified behavior

### Owner scope and request boundary

MemoryPreferences derives principal and root from one validated configuration snapshot. It grants dashboard:owner all native fact categories and projects, plus proposal review and manual approval. It does not grant proposal creation or automatic approval. The request envelope accepts only tool and arguments. Client-supplied scope metadata is rejected.

The unchanged service validator rejects unknown fields and invalid reference types. Real HTTP probes covered boolean revision, nonexistent revision, empty edit, private-tagged resolution note, an extra dry_run argument, and an automatic decision request with confidence_threshold. These requests were rejected or conflicted and left the native target and queue unchanged. The automatic request was rejected at the public schema boundary; this probe does not claim it exercised the deeper auto_apply permission branch.

Three malformed request envelopes returned HTTP 400. The existing API relies on authenticated Hermes dashboard mounting. The synthetic ASGI test app mounts the router directly, so it does not independently verify authentication middleware. Authentication mounting was unchanged in this unit and was not re-audited.

### Exact references and native outcomes

The UI sends each displayed proposal reference intact, including its revision. It displays proposed text, target, rationale, writer, and revision. It provides accept, reject, edit, and applied-elsewhere controls. It exposes no activation or automatic approval control.

Actual HTTP requests against the prepared native source verified all four decisions:

| Decision | Stored native status | Target behavior |
|---|---|---|
| accept | accepted | Proposed text appears in target |
| reject | rejected | Target remains byte-identical |
| edit | edited | Owner replacement text appears in target |
| applied_elsewhere | applied-elsewhere | Target remains byte-identical |

Each committed row disappears from pending review. Native resolved review reports the expected status. Responses contain decision metadata and no full row. Repeating the exact request returns the same receipt. A new request using the resolved proposal's old reference returns conflict. Configuration bytes remain unchanged across these review operations.

### Truthful UI outcomes

The existing SDK tests verify a successful decision removes the refreshed pending row and a conflict leaves the proposal visible with the conflict reason. The edit request carries the owner's draft.

Four additional SDK probes simulated an acknowledged commit followed by failure of the pending-list refresh. Each displayed its committed outcome plus an explicit refresh warning:

- Change accepted. Could not refresh pending changes: Synthetic refresh failure
- Change rejected. Could not refresh pending changes: Synthetic refresh failure
- Change edited. Could not refresh pending changes: Synthetic refresh failure
- Change applied-elsewhere. Could not refresh pending changes: Synthetic refresh failure

The UI preserves the previously displayed list when refresh fails. The warning identifies that list as unrefreshed; any later attempt still carries the original reference and is protected by the backend conflict check. The probes verified exact references and decision-specific edit or note payloads.

These are SDK component tests with controlled fetch results, not browser or network end-to-end tests. Real HTTP and native behavior were exercised separately. A transport failure before the browser receives a committed receipt is outside this acknowledged-result refresh probe.

### Existing controls and capability status

The 7 preferences tests still verify installation root checks, concurrent enrollment/revocation root checks, health status without ownership activation, strict owner fact review, and sharing disable behavior. The 9 combined dashboard SDK tests cover existing model selection/settings behavior, preparation and reduced host safety states, minimal revoked grants, fact search references, and default project-only read grants.

The native capability action checks the five expected native decision exports. Status reports review availability only after native health succeeds and the proposal module is present. This is availability detection, not a claim that activation gates passed. The capability probe itself does not approve or resolve a proposal.

## Tests and evidence

| Gate | Result | Raw output |
|---|---|---|
| test_memory_preferences.py | 7 passed | raw/preferences.txt |
| test_memory_dashboard.py | 2 passed | raw/dashboard.txt |
| test_memory_dashboard_ui.cjs plus test_dashboard_ui.cjs | 9 passed | raw/ui.txt |
| Four UI committed-result refresh-failure probes | All passed | raw/ui-probe.txt |
| Four real HTTP manual decisions, retry and stale references | All passed | raw/http-probe.txt |
| Six negative argument cases and three malformed envelopes | All passed | raw/http-probe.txt |

Commands are saved in raw/commands.txt. The Python test environment was /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python. The native source was /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-proposal-delegation-fixed/lifeos/LifeOS/install.

The existing dashboard unittest uses its default owned prepared host source, source-gate-20260930-native/hermes. The additional HTTP probe explicitly uses the requested sibling source-gate-20260930-proposal-delegation-fixed/hermes. Neither imports a live Hermes installation.

The first HTTP probe attempt failed before any HTTP request because its script did not put prepared Hermes source on sys.path. That setup error is preserved in raw/http-probe-setup-failure.txt. Adding the explicitly allowed prepared source path to the probe resolved the setup issue. No implementation change was involved.

Raw scripts are raw/probe_http.py and raw/probe_ui.cjs. The latter reuses the existing SDK test harness and adds four controlled refresh failures. Initial and final source hashes, source snapshots, fixture hashes, and the reviewed diff are in raw/. raw/source-drift.json is empty.

## Remaining limits for Adrian's review

No full browser runtime test was performed. Authentication mounting and generic host admission were unchanged and not repeated. Existing installation activation, historical source coverage, restricted prompts, lifecycle, and backup/recovery release gates remain open as previously declared. This report approves only the tested owner proposal preferences behavior for the development checkpoint.
