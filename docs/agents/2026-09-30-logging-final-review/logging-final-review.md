Date: 2026-09-30
Reviewer role: Independent final logging reviewer
Question: Does the current development recorder still have meaningful defects in credential filtering, evidence fidelity, or preservation of native hook behavior?
Model: GPT-6 via Codex, inherited from the primary agent. The harness does not expose a more specific service model identifier.

## Result and reviewed state

The reviewed baseline is commit `2cc9303850690a07b4f410a65f335ce631eadb3d` on `feature/development-capture`. I confirmed two remaining defects and notified the primary agent immediately. The primary agent implemented both corrections during this review. I independently reran the original reproducers against a snapshot of the corrected working tree and verified both corrections. The corrected 26-test suite passes locally in 6.759 seconds.

There are no meaningful confirmed open findings from this bounded review. That statement applies to the corrected source hashes recorded in `corrected-probes.json`, rather than the original commit or the currently deployed observer on another machine. This reviewer did not deploy the corrected code or inspect live captured data.

The corrected recorder source hashes include:

| File | SHA-256 |
| --- | --- |
| `store.py` | `6505d9cc7e68940c4b476ea99ef5479abc00dd2918049a0fb6f472f17fc1faac` |
| `analysis.py` | `6d2d23be5778b99976018fab81597fec905fda2f3d490c41afc22e3720779dc4` |
| `instrument.py` | `d13042fdb5775059ed070f5597894625345cbfd917782143164651b14b9dd90d` |

## Confirmed baseline findings and independent correction checks

### P1: A declared Bearer credential leaks when output echoes its bare token

Baseline location: `development/hook_capture/store.py`, `declared_secrets`, string handling. Corrected location: lines 60 to 63.

The baseline learns the complete credential field value `Bearer SYNTHETIC-BEARER-CREDENTIAL-482739`. It does not learn `SYNTHETIC-BEARER-CREDENTIAL-482739` itself. Structural filtering removes the Authorization field and TOKEN_SHAPE removes complete Bearer strings, but a sibling stdout or echo field containing the bare token remains intact. A later artifact also leaks the token because the recorder still has not learned it.

The baseline primitive probe stores this exact synthetic result:

```json
{"headers":{"Authorization":"[REDACTED]"},"stdout":"SYNTHETIC-BEARER-CREDENTIAL-482739"}
```

The real subprocess hook prints JSON containing `authorization: Bearer <token>` and `echo: <token>`. Against the isolated baseline source, the token remains in six observed stages: `process.completed`, `run_command.returned`, `hook.completed`, `response.parsed.entered`, `response.parsed.returned`, and `translation.returned`. Native and traced bridge outcomes both print `null`, both processes exit 0, and both stderr streams are empty. This is a declared credential echo and does not depend on recognizing an unknown credential in arbitrary prose.

The primary agent's correction learns the token body from the existing TOKEN_SHAPE matches before artifact serialization. The independent corrected probe reports `token_learned: true`, removes the token from both the first and later primitive artifacts, and reports an empty real hook `leak_stages` list. Native and traced outcomes remain identical, with empty stderr.

### P2: Reusing an artifact path skips validation of a different expected digest

Baseline location: `development/hook_capture/analysis.py`, artifact integrity cache. Corrected location: lines 71 to 84.

The baseline cache uses only the relative artifact path. After one correct reference validates that path, a later event can name the same path and an incorrect SHA-256 value without triggering another check. This bypasses the analyzer's declared reference integrity check.

The independent probe emits one valid artifact event, then appends a second event with a distinct event ID and sequence. The second event retains the artifact path and changes its declared digest to 64 zeros. The baseline indexes both events and reports `integrity_issues: {}`. The artifact itself remains unchanged and valid, so this isolates reference validation from decompression or file corruption.

The primary agent's correction keys validation by both path and expected digest, and excludes references that failed validation from inventory ingestion. The independent corrected probe still indexes the two event records but reports `integrity_issues: {"artifact_error": 1}`. The added regression test passes in the complete 26-test run. I inspected the change and found no hook execution path affected by this offline correction.

## Verification and evidence

| Artifact | Evidence |
| --- | --- |
| `local-tests.txt` | Exact initial output: 24 tests pass in 6.024 seconds. |
| `working-tree-tests.txt` | Exact corrected output: 26 tests pass in 6.759 seconds. |
| `final_probes.py` | Reproducer that copies development source into a disposable directory and runs real local hooks. `--revision` restores recorder Python source from the named Git revision. |
| `baseline-probes.json` | Original commit hashes, both baseline defects, and malformed-record recovery result. |
| `baseline-probes-stderr.txt` | Empty stderr from the baseline probe orchestrator. |
| `2cc9303-real-bearer-hook-artifacts.json` | Raw synthetic event records and expanded artifacts from the baseline real hook. |
| `local-probes.json` | Intermediate snapshot after the Bearer correction and before the integrity correction. |
| `local-probes-stderr.txt` | Empty stderr from the intermediate probe orchestrator. |
| `corrected-probes.json` | Corrected source hashes and independent passing reproducers for both corrections. |
| `corrected-probes-stderr.txt` | Empty stderr from the corrected probe orchestrator. |
| `working-tree-real-bearer-hook-artifacts.json` | Raw synthetic event records and expanded artifacts from the latest corrected real hook. |

Reproduce the original commit:

```bash
python3 docs/agents/2026-09-30-logging-final-review/final_probes.py --revision 2cc9303
```

Reproduce the current working tree:

```bash
python3 -m unittest discover -s development/tests -v
python3 docs/agents/2026-09-30-logging-final-review/final_probes.py
```

Each real probe configures the subprocess startup observer as disabled before explicitly installing the selected isolated source. The probe uses the unchanged public bridge and real local shell hook processes. It does not import `hermes_bootstrap`, run a build, contact remote hosts, or send a Discord message.

An additional malformed-record boundary probe inserts a JSON object containing 1,100 nested array levels between two valid events. Both the baseline and corrected analyzers report one `invalid_event` and retain the two valid events. This probe did not establish another defect.

The existing real tests cover native versus observed hook outcomes, large streams, timeout evidence, detached execution, HTTP read limits, duplicate registrations, settings origin identities, malformed output and evidence, encoded transport, source drift, credential declarations and echoes, capture failure reporting, and selective thread context propagation. I inspected the observers and analyzer within this scope. No new native behavior discrepancy was established.

## Limits and review items

The corrected local reproducers establish these two fixes. They do not establish deployment, a live Hermes turn with the corrected observer, every registration's semantic behavior, every backend permission case, or comparative observer latency. Historical immutable artifacts are unaffected by these corrections and were not inspected or rewritten.

Review the final committed source against the corrected hashes before deployment. Keep the distinction between executed hook evidence and actual host enforcement when using the reports for later parity work. The source-pinned observer remains under `development/`, outside the public plugin subtree.

This reviewer wrote only review reports and synthetic probe artifacts in this review directory. The primary agent made implementation edits concurrently. I made no implementation edits, commits, pushes, service changes, account configuration changes, memory calls, or journal calls.
