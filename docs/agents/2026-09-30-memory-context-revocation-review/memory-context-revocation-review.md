# Memory context revocation review

Date: 2026-09-30  
Role: Independent code and integration reviewer, delegated by the primary implementation agent  
Question: Does the revised inactive-context admission preserve revocation through child processes, and do the owner preferences API and UI preserve configuration and authentication boundaries?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The previously confirmed retained-context leak is closed in the reviewed snapshot. The unchanged child reproduction now stops at re-admission with `MemoryAdmissionError`, before the former leaking request. An adapted negative probe catches the expected refusals, preserves the original fixture and retained context, and confirms zero HTTP requests for disabled or deleted ownership. A fresh inactive conversation still sends its public synthetic request.

Two new preferences defects remain in the reviewed snapshot:

1. **Medium: enrollment and revocation can operate on another installation after a concurrent configuration root change.**
2. **Low: a valid client grant with omitted optional permission lists crashes the new preferences panel.**

Both findings were sent to the primary agent with reproduction artifacts. Implementation fixes made after these snapshots need a separate verification. This review does not approve activation.

## 1. Installation validation does not cover the enrollment/revocation mutation

Locations in the reviewed source: `lifeos_hook_bridge/memory_preferences.py:77` and `:86`; the delegated configuration mutation is in `lifeos_hook_bridge/memory_sharing.py`.

`MemoryPreferences.enroll()` and `revoke()` check the installed root with `_configuration()`. They then call `MemorySharing`, which acquires its locks and loads the configuration again. Neither mutation checks that this second configuration still refers to the root validated by the preferences request.

### Reproduction

`raw/probe_preferences_race.py` uses a temporary native fixture, private temporary SSH files, the real configuration publisher, and a thread barrier. An instrumented subclass calls the actual `_configuration()` and pauses immediately after it succeeds. The other thread changes `root` through the real `MemoryConfiguration.update()`. The preferences operation then continues unchanged.

Observed results in `raw/preferences-race.jsonl`:

| Operation | Result after root changes | Configuration modified | SSH keys modified |
|---|---|---|---|
| Enroll | `status: enrolled`, enabled client added for the other root | Yes | Yes |
| Revoke | `status: revoked`, client disabled for the other root | Yes | Yes |
| Sharing toggle control | `MemoryUnavailable`, different-installation message | No | No |

The barrier controls scheduling only. It does not replace the configuration loader, writer, lock, enrollment implementation, or SSH publication. The other root is a synthetic path. This probe establishes incorrect configuration and key mutation, not a demonstrated transfer of another installation's facts.

The preferences request is already authenticated as the dashboard owner. This is a configuration consistency defect under a concurrent root change, not an unauthenticated remote privilege escalation. Enrollment has the larger consequence because it enables a credential and globally enables sharing on the changed configuration.

**Required correction:** carry the expected installation identity into both configuration update callbacks and validate it under the same lock that publishes the mutation. The existing sharing toggle provides the relevant behavior. Rejection must leave the configuration and SSH keys unchanged.

## 2. Optional client permissions crash the UI

Locations: `lifeos_hook_bridge/dashboard/dist/index.js:114` and `:115`; raw grant output in `memory_preferences.py:50`.

The configuration validator permits an entry such as `clients: {minimal: {enabled: false}}`. The configuration validator accepts missing `read`, `write`, and `projects`; service code supplies permission defaults when resolving such a grant. `MemoryPreferences.status()` returns the raw grant without these defaults. The React component calls `.join()` on each field without supplying a default.

`raw/minimal-grant-configuration.json` records a successful real configuration save/load and a `prepared` status response containing this minimal client. `raw/probe_ui_minimal_grant.cjs` executes the actual bundle through the existing SDK unit fixture and adds an assertion that this valid status response renders.

The additional assertion fails with:

```text
TypeError: Cannot read properties of undefined (reading 'join')
```

The stack points to bundle line 114 inside `MemoryPreferences`. A revoked client can therefore prevent the entire memory panel from rendering even though the underlying configuration is valid. There is no data disclosure in this probe.

**Required correction:** normalize the optional grant fields in the preferences status response, or give the renderer defaults that match configuration semantics. Include the default declared route, `unknown`, when omitted. Verify against a response generated from a real accepted minimal configuration.

## Retained-context closure evidence

The original reproduction is unchanged at `../2026-09-30-memory-admission-closure/raw/probe_children.py`. Its output and expected nonzero exit are preserved in `raw/unchanged-child.jsonl` and `raw/unchanged-child.stderr`. It stops exactly at the newly refused inactive admission.

The adapted script is `raw/probe_children_negative.py`. It catches expected admission/binding errors and asserts that no HTTP call occurs at those refusals. It continues with the original child adapter, original retained environment, actual model provider integration, and localhost recorder. All 18 cases are summarized in `raw/child-summary.json` and recorded in full in `raw/child-negative.jsonl`.

| Case | Observed result |
|---|---|
| Approved raw child | Exit 0, one localhost request |
| Enabled child missing detailed context | Exit 1, zero requests |
| Configuration/profile mismatch | Exit 1, zero requests |
| Disabled configuration, original inherited context | Exit 1, zero requests |
| Disabled re-admission and environment rebind | Both refuse before a request |
| Disabled configuration, sealed session ID only | Exit 1, zero requests |
| Deleted re-admission and environment rebind | Both refuse before a request |
| Deleted configuration, original inherited context | Exit 1, zero requests |
| Deleted configuration, sealed session ID only | Exit 1, zero requests |
| Deleted configuration, recorded session with cleared process binding | Admission refuses |
| Fresh inactive conversation after clearing old process binding | Exit 0, one public synthetic request |
| Approved actual Hermes provider child | Exit 0, one localhost request |
| Unapproved provider route | Exit 1, zero requests |
| Provider child missing detailed context | Exit 1, zero requests |
| Provider child after forget | Exit 1, zero requests |
| Legacy native Claude fallback with inherited context | Exit 1, zero requests |

`bind_environment()` seals the configuration, profile home, and session ID. The bridge supplies the payload session ID. `check_call()` uses the sealed child session ID when host metadata and explicit arguments do not supply one. The new inactive admission path checks retained context before clearing the process binding. Together these changes close the reproduced revocation path.

The probe intentionally clears the prior process binding before testing a genuinely fresh inactive conversation. It does not relabel a retained prompt as a fresh conversation. The fresh request uses a separate public marker.

The unchanged terminal dispatcher probe still reaches its downstream callback. The unchanged SSH collision probe still preserves the unrelated key, and its concurrent configuration updates retain all 32 changes. See `raw/terminal-probe.jsonl` and `raw/sharing-probes.jsonl`.

## Actual dashboard authentication integration

`raw/probe_dashboard_auth.py` copies the plugin into a temporary profile, writes an explicit enabled-plugin configuration, and imports the owned prepared Hermes `web_server`. The real host discovers and mounts the plugin API. The probe uses the actual FastAPI middleware stack with a synthetic current native fact.

| Authentication | Owner search outcome |
|---|---|
| No session token | HTTP 401 |
| Invalid session token | HTTP 401 |
| Valid temporary session token | HTTP 200, synthetic fact returned |
| Cookie-gated mode with no session | HTTP 401 |

`raw/dashboard-auth.jsonl` contains the complete responses. No custom replacement authentication middleware was used. No real OAuth provider was called. This verifies the existing host token gate and rejection without a cookie session; it does not independently certify a production identity provider.

The plugin router has no standalone authentication and must remain mounted behind the host middleware. Its unrestricted owner scope assumes that an authenticated dashboard user is authorized to administer that profile's memory. The reviewed host mount only imports enabled trusted user or bundled plugin backends, and the runtime plugin gate can refuse disabled plugins. The plugin routes are absent from the public API allowlist.

## Tests

All requested suites used the new shared environment at `/home/outsider/.cache/lifeos-plugin-memory/memory-test-env/bin/python`. The host suite used the canonical runner and the owned `source-gate-20260930-native/hermes` source.

| Gate | Result | Raw output |
|---|---|---|
| Full `test_memory_*.py` suite | 92 passed in 52.050 seconds | `raw/memory-tests.txt` |
| Hermes provider suite | 7 passed in 4.115 seconds | `raw/provider-tests.txt` |
| Claude adapter suites | 7 passed in 1.596 seconds | `raw/adapter-tests.txt` |
| Four canonical host test files | 131 passed, 0 failed | `raw/host-tests.txt` |
| Existing dashboard API suite | 14 passed | `raw/dashboard-api-tests.txt` |
| Memory and existing dashboard UI units | 6 passed | `raw/ui-tests.txt` |
| Additional minimal-grant UI probe | Existing 2 pass, additional assertion fails | `raw/ui-minimal-grant.txt` |

The full memory suite includes actual native tools, installed MCP transport, isolated localhost SSHD, the child HTTP recorder, and the native FastAPI preferences test. The Node UI tests are SDK unit tests with a simulated renderer and fetch responses, not browser integration tests. The authenticated dashboard probe supplements the router-only FastAPI test.

## Source and evidence boundaries

`raw/hashes.json` and `raw/snapshot-*` preserve the starting review sources. `raw/final-hashes.json` records the added UI and host authentication files. `raw/source-drift.json` records a test-only change: the primary agent began adding a root-race regression to `tests/test_memory_preferences.py` after receiving the finding. That updated test is saved separately as `raw/closing-tests__test_memory_preferences.py`. The 92-test result refers to the original captured suite, before that added test. No claim is made that a later implementation fix was verified here.

Exact test and probe commands are in `raw/commands.txt`. All synthetic fixture files were disposable. Source snapshots and probe outputs remain in this report directory.

No implementation files were edited or committed. No live Hermes runtime, fleet host, production memory, or journal was accessed. Native proposal approval, filtered restricted prompts, complete child/session lifecycle coverage, ownership activation, backup/restore/update behavior, and release approval remain explicitly open. The UI correctly avoids offering ownership activation and displays these unfinished gates.

## What deserves Adrian's review

The configuration lock boundary is the remaining correctness risk: the installation selected by a preferences request must be the installation modified when credentials change. The UI failure is a smaller accepted-input compatibility issue. The retained-context fix is verified for the concrete raw and Hermes provider child routes above; this is not a claim that every native source or lifecycle path has been activated and audited. No browser runtime verification or production authentication-provider verification was performed.

## Primary-agent fix notification after review

After these findings and snapshots were saved, the primary agent reported fixes: `MemorySharing` receives the expected installation root and rechecks it inside enrollment and revocation configuration mutations; the UI supplies optional client-field defaults. The primary agent reports six preferences tests and seven UI tests passing. Those are primary-agent results, not independent verification by this review. A subsequent snapshot closure should rerun both unchanged reproductions against those fixes.
