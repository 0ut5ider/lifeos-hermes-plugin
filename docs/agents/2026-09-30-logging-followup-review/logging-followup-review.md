Date: 2026-09-30
Reviewer role: Independent follow-up code and evidence reviewer
Question: Are all eight initial logging findings resolved, and do the corrected recorder and analyzer support truthful health and correlation conclusions?
Model: GPT-6.1-Sol, inherited from the parent agent

## Reviewed state and result

This report reviews commit `12042c990e15a66d31433ab42198d6f6484e7225` on `feature/development-capture`. The reviewer loaded the coding-rules skill, read the initial independent report and correction note, inspected the recorder and native bridge boundaries, ran the 21-test suite, and independently reproduced the relevant behaviors with synthetic fixtures.

Six of the eight original findings are resolved in the reviewed paths. Two remain partially resolved: declared credential echoes still escape through the supported encoded remote protocol, and malformed evidence recovery still fails or silently ignores certain inventory and numeric shapes. These are confirmed defects, not hypothetical limits. The 21 existing tests all pass; their passing result does not cover these remaining cases.

The primary agent received both defects during the review and said it would reproduce and fix them. This report describes `12042c9`; it does not certify subsequent edits, a later deployment, or full semantic parity.

## Confirmed open findings

### P1: A declared credential echo survives in the encoded native transport artifact

Locations: `development/hook_capture/instrument.py:304`, `:334`, especially `:342` to `:343`; credential discovery in `development/hook_capture/store.py:172`.

Reproduction: the unchanged native `run_project_hook` executes its real Bash protocol through a local subprocess backend. A hook file prints JSON containing `api_key` and an `echo` of that same synthetic value. The protocol base64-encodes stdout and stderr. The observer records `transport.completed` before `remote_hook.returned` exposes the decoded CompletedProcess object.

`transport_output` decodes each frame and calls `safe` using the recorder's existing secret list. `safe` removes the `api_key` field but does not discover its value to remove the sibling `echo`. The observer re-encodes that partially filtered output. Recorder.artifact then sees the encoded wire, so its corrected `declared_secrets` traversal cannot discover the declaration. The stored stdout frame retains the credential under `echo`.

Independent output: both baseline and traced subprocesses exit 0 and return the same result. Exactly `transport.completed` leaks the value after decoding its stored base64 frame. The later decoded return artifact filters it. Ordinary command and HTTP hook artifacts pass the corresponding independent probes.

Impact: recognizable credentials declared in the supported native remote protocol can remain in immutable capture artifacts. A literal scan of compressed JSON text can miss the encoded leak. This is within the explicitly supported remote protocol, so the documented limit for unknown prose or unrelated encodings does not apply.

Minimum fix: discover credential declarations across all decoded input and output protocol components before filtering any component or re-encoding the wire. Use a shared discovered-value set so declarations in stdout also remove echoes in stderr and other components. Keep the native transport result unchanged. Add a regression that executes the real native frame and decodes every captured frame when checking stored evidence.

Evidence: `followup_probes.py`, `local-probes.json`, and `local-probes-second-pass.json`, key `actual_native_encoded_transport`. The fixture uses a real local shell process to verify the native protocol and its observer. It does not claim to test SSH selection, Docker selection, or a live network backend.

### P2: Malformed inventory and oversized event integers still defeat recovery

Locations: `development/hook_capture/analysis.py:54` to `:59`, `:80` to `:92`.

Reproductions:

1. An `inventory.observed` artifact contains one registration whose `matcher` is `[]`. Its JSON and digest are valid. SQLite raises `ProgrammingError: Error binding parameter 4: type 'list' is not supported` at line 84. Rebuild stops before the following valid event can be processed.
2. An otherwise valid event has `sequence=2**100`. The new validation accepts it as a positive integer. SQLite raises `OverflowError: Python int too large to convert to SQLite INTEGER` at line 90. Rebuild stops.
3. An inventory artifact has top-level value `[]`, or `registrations` is the string `bad`. Rebuild completes and retains the surrounding events, but returns `integrity_issues={}` and `known_registrations=0`. The exceptions are swallowed at lines 86 to 87. The comment that the earlier integrity check reports damaged artifacts is incorrect for these schema failures: the compressed bytes and digest are valid.

Impact: one malformed inventory record can prevent analysis of valid following records. Other malformed inventories disappear from the registration denominator without a health issue. A summary with no integrity issues can therefore conceal lost coverage evidence. The oversized integer case is a concrete malformed-evidence case, not a normal recorder sequence expected to reach that size.

Minimum fix: validate inventory object, registration-list, registration-object, and scalar-column shapes before inserting registrations. Record a sanitized inventory issue when that schema is invalid. Check signed SQLite integer bounds for stored numeric fields. Continue through the next valid record. Do not merely suppress SQLite exceptions without reporting the lost evidence.

Evidence: `local-probes.json` confirms the exceptions; `local-probes-second-pass.json` adds the silently ignored inventory cases. The ordinary array/null event, bad data_ref, bad status, and corrupt-deflate fixtures recover correctly, recording four invalid events and one artifact error while retaining both valid surrounding events.

## Disposition of the eight initial findings

| Initial finding | Disposition at 12042c9 | Independent evidence |
| --- | --- | --- |
| Declared credentials survive supported result representations | Partially resolved | Fresh recorders separately filter JSON, bytes, dataclasses, CompletedProcess, TimeoutExpired, and partial JSON. The real command hook filters all four former leak stages. The native encoded transport still leaks an echo. |
| HTTP headers and URL credentials bypass recognition | Resolved in reviewed paths | Fresh URL/header fixtures filter values and echoes. A real loopback HTTP hook filters query and response credentials, including decoded response bytes, with the same native outcome. |
| Known capture losses disappear from summaries | Resolved | NaN and cycle storage failures in two processes produce `known_lost_events=3` and `capture_failure_processes=2`; repeated cumulative reports do not inflate the total. |
| Malformed records and corrupt deflate stop analysis | Partially resolved | Original malformed event/reference/status and corrupt-deflate cases recover. Malformed inventory columns and oversized integers still abort; other inventory schemas disappear without an issue. |
| Settings origins merge registration identities | Resolved | Distinct observed settings paths produce distinct registration IDs and two indexed registrations. Reobserving the same path preserves its ID. The full suite also executes two actual bridges with identical hook lists. |
| Recorder manifest drift goes unchecked | Resolved in reviewed activation path | A separate deliberately invalid manifest fixture records one capture gap, records the actual source manifest, activates no hook observers, and preserves the native result. Ordinary hook fixtures use a valid manifest. |
| Host records omit an available native turn ID | Resolved in reviewed identity path | Two turns in one session retain their correct turn ID on both entered and returned wrapper records. Direct read-only native source inspection confirms the patched boundaries receive `agent`, and native `tool_hook_ids` uses `_current_turn_id`. A new live host turn with this revision was not observed. |
| Failed hooks are labeled completed | Resolved | A failed-only fixture reports one terminal outcome, one failure, zero successful executions, and zero interventions. |

## Health and correlation conclusions supported by the evidence

`known_lost_events` now states a useful lower bound on reported recorder failures. It cannot reveal a process that never writes successfully or a final failure with no later successful event. The documentation says this plainly. Zero reported losses supports the absence of reported loss, not complete capture.

The corrected registration identity includes observed origin and execution scope. Stable identity across runs is acceptable here. The inventory count is documented as a historical union of observed registration versions. It must not be presented as the count of currently installed hooks. The malformed inventory finding weakens that denominator until its correction is verified.

Span, invocation, callback, session, and turn IDs support following observed boundaries. They do not establish that a directive was enforced, that a hook's intended file or memory effect occurred, or that all permission paths preserve native behavior. The multi-turn identity probe verifies the available native turn field is retained by the wrapper; it does not complete the host enforcement matrix.

The failed-only summary uses truthful terminal and failure labels. A terminal outcome with exit code 0 is execution evidence. The analyzer's note explicitly denies a semantic parity conclusion. No result in this review establishes full parity.

The ordinary-content policy, unknown arbitrary prose/encoding limit, immutable historical artifacts, lack of automatic retention deletion, and absent comparative latency study are documented limits. They are not findings added by this review. The confirmed native-protocol leak is outside the unrelated-encoding limit.

## Deployment, installer boundary, and external effects

The read-only `.212` snapshot reports 1,184 events, zero reported losses, configuration mode 0600, capture-root mode 0700, matching runtime fingerprints, and a recorder manifest that matches its files on disk. Local comparisons establish that those files are exactly the baseline `8995ac2` recorder sources, rather than `12042c9`. Existing host context, stop, and tool boundary records still lack turn identity. That snapshot therefore does not certify the corrected runtime. Historical process manifests contain three observed versions; they must be interpreted per process instead of treating the current disk manifest as proof for every historical record.

The public installer selects `lifeos_hook_bridge/`. Static inspection of its 43 tracked runtime files finds no recorder package, development directory, or rawdata. Native runtime files are unchanged by the reviewed correction commit. No public installer was executed in this review.

This reviewer made no implementation changes, commits, pushes, restarts, server-setting changes, messages to external services, or memory/journal calls. Only synthetic probe scripts/results and this report were written locally. No real captured content, credentials, or raw real artifacts were exported. Remote actions used direct stdlib Python with `-S` to aggregate metadata and read inspected host source boundaries. No remote synthetic suite was run, and no Hermes bootstrap, package manager, build, historical host-effect probe, `.211`, or `.213` action occurred.

## Saved evidence and reproduction

| File | Contents |
| --- | --- |
| `local-tests.txt` | Exact unittest output: 21 tests pass in 6.736 seconds. |
| `followup_probes.py` | Synthetic reproducer for all eight findings and the remaining boundary cases. |
| `local-probes.json` and `local-probes-stderr.txt` | First independent probe results and expected loss diagnostics. |
| `local-probes-second-pass.json` and companion stderr | Repeated probes with fresh recorders per supported representation and additional malformed inventory cases. |
| `deployment_metadata.py` | Stdlib-only count and manifest aggregation used for `.212` metadata. |
| `deployment-metadata.json` and companion stderr | Count-only deployment snapshot; stderr is empty. |
| `host-source-boundaries.txt` | Read-only native source signatures and turn-identity helper. |
| `source-identities.json` | Reviewed full commit, source hashes, baseline deployment comparison, and runtime boundary check. |

Local reproduction from the reviewed checkout:

```bash
python3 -m unittest discover -s development/tests -v
python3 docs/agents/2026-09-30-logging-followup-review/followup_probes.py \
  --development development --plugin lifeos_hook_bridge
```

The synthetic stderr deliberately reports three storage failures: one NaN ValueError, one cycle RecursionError, and another NaN ValueError. These diagnostics are expected test evidence. Command, HTTP, drift, and native protocol subprocess stderr are empty.

## What deserves Adrian's review

The remaining credential leak deserves priority because the observer can preserve an unseeded declared credential inside its supported encoded transport. Review the correction against decoded stored frames, including cross-stream echoes, before relying on literal-only scans or activating the reviewed revision.

Review malformed inventory handling as a health issue as well as an exception issue. A missing registration denominator with an empty integrity report is misleading. Keep the historical-union meaning explicit after that fix.

This review does not sanitize prior immutable artifacts or verify a corrected live host turn. Any historical cleanup remains a separately authorized operation that must preserve reference integrity. Recheck the later correction commit and its new regression results before reporting zero meaningful open findings.
