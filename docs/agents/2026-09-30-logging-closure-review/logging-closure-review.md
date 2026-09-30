Date: 2026-09-30
Reviewer role: Independent logging closure reviewer
Question: Do the current logging fixes close meaningful defects, and do fresh native fixtures expose another blocker?
Model: GPT-6.1-Sol, inherited from the parent agent

## Reviewed state and decision

The reviewed source corresponds to commit `8de64ff63bbd04fe39378af9887a73ccf40a84cd` on `feature/development-capture`. The first snapshot was collected while the primary agent's changes were uncommitted. The final snapshot confirms identical hashes for every recorder source, the test file, and the development README after the primary agent committed them. The reviewer loaded the coding-rules and experiment-method skills and inspected the applicable shared AGENTS instructions. No project or ancestor AGENTS.md file was present in the inspected paths.

All 26 existing tests pass independently in 6.492 seconds. The latest Bearer token and artifact reference corrections pass additional independent probes. The review finds two related credential filtering defects: Set-Cookie declarations do not remove echoed cookie values, and Basic authorization declarations do not remove echoed credential components. Deployment closure is blocked by these findings.

## Confirmed finding

### P1: A declared cookie credential survives an echoed response body

Locations: `development/hook_capture/store.py`, `declared_secrets`; `development/hook_capture/instrument.py`, `patch_http.Response.read`.

The HTTP fixture is a real local server with a native HTTP hook. It returns the header `Set-Cookie: session=SYNTHETIC-CLOSURE-COOKIE-192837; HttpOnly; Path=/` and a JSON body with an ordinary `echo` field containing the session value. Both traced and native hooks produce the same result. The traced run creates 19 events.

The stored `http.response_read` artifact correctly replaces its Set-Cookie header with `[REDACTED]`. However, decoding the stored base64 body shows that the declared session value survives. The value also survives five later artifact stages: `run_http.returned`, `hook.completed`, `response.parsed.entered`, `response.parsed.returned`, and `translation.returned`.

Credential discovery learns the complete cookie header string. It does not learn the cookie value within that string. Exact string replacement cannot remove a body echo that contains only the cookie value. The HTTP response artifact contains both the declaring header and the echoed body, so discovery can learn the value before any part of that artifact is filtered. This is analogous to the fixed Bearer body defect. It concerns a recognized credential header in a supported HTTP boundary.

The smallest correction is to discover actual cookie values from Cookie and Set-Cookie declarations, then use the discovered values when filtering the whole artifact and later artifacts. Set-Cookie attributes such as Path and SameSite are not additional credentials. Do not change the native response. Add a regression that uses the real loopback HTTP hook and decodes stored byte representations before checking for the value.

Evidence: `closure-probes.py` is the complete reproducible fixture. `closure-probes.json`, key `real_cookie_http_hook`, records unchanged native outcome, redacted header, and all six leaking stages. `closure-probes-stderr.txt` is empty. Only synthetic credentials and synthetic response bodies were used; no real capture was inspected or exported.

### P1: Basic authorization components survive a recognized declaration

Location: `development/hook_capture/store.py`, `declared_secrets`.

At the primary agent's request, the reviewer also checked Basic authorization component discovery. A real native command hook emits a JSON object with an Authorization header using the Basic scheme, an ordinary `echo` field containing the password, and `encoded_echo` containing the base64 user/password pair. The input password and encoded value are entirely synthetic. The native and traced results match, and the traced run creates 19 events.

The complete Authorization header is redacted, but both component echoes survive in six stages: `process.completed`, `run_command.returned`, `hook.completed`, `response.parsed.entered`, `response.parsed.returned`, and `translation.returned`. The test deliberately uses the ordinary key `echo`, because a key containing `password` would itself declare and filter that value, hiding the Basic parsing defect.

Credential discovery learns the whole `Basic <base64>` string. It learns neither the encoded token body nor the password in the decoded user/password pair. These are recognizable components of the declared authentication protocol. This differs from guessing an unrelated encoding in arbitrary prose.

The correction should learn the Basic encoded token body and the decoded password before filtering the artifact. Validate the Basic framing and base64 rather than treating arbitrary encoded text as a declaration. Preserve the native hook output. A primitive regression plus the real command fixture must verify both ordinary password echoes and encoded credential echoes.

Evidence: `basic-probes.py` and `basic-probes.json` record the exact fixture, both sets of six leak stages, unchanged native outcome, and the recorder source hashes. This probe ran after the primary agent began the cookie correction; its contemporaneous hashes are preserved separately rather than attributed to `8de64ff`. `basic-probes-stderr.txt` is empty. No production data or external system was accessed.

## Verified corrections

| Boundary | Independent result | Evidence |
| --- | --- | --- |
| Bearer declaration and bare token echo in a real command hook | Native result unchanged; no leaking artifact stage | `closure-probes.json`, `real_bearer_hook` |
| Valid artifact reference followed by a different expected digest | Both events retained; one artifact error; invalid inventory cannot add registrations | `closure-probes.json`, `invalid_reference_cannot_index` |
| Valid and invalid digest references in either order | Each order reports one artifact error; the valid inventory still adds exactly one registration | `closure-probes.json`, `reference_orders` |
| Declared credential and echo in native encoded remote transport | Native result unchanged; no stored decoded credential leak | `followup-probes.json`, `actual_native_encoded_transport` |
| JSON, bytes, dataclass, command result, timeout, and partial JSON representations | No declared credential leaks in independently rebuilt fixtures | `followup-probes.json`, `supported_representations` |
| Real native command and HTTP result capture | Native outcomes unchanged; former credential leak stages are clean | `followup-probes.json`, `actual_command` and `actual_http` |
| URL password, query, fragment, and X-API-Key declarations | Stored echoes filtered | `followup-probes.json`, `url_and_header_declarations` |
| Invalid inventory fields and shapes | Each fixture retains two valid events and reports one invalid inventory issue | `followup-probes.json`, `extra_malformed_inventory_*` |
| Oversized indexed integer | Rebuild retains following valid events and reports one invalid event | `followup-probes.json`, `extra_malformed_sequence_overflow` |
| Corrupt artifact and malformed event recovery | Two valid events survive, with one artifact error and four invalid events | `followup-probes.json`, `malformed_recovery` |
| Known capture loss | Three losses across two processes are reported without cumulative double counting | `followup-probes.json`, `loss_summary` |
| Distinct registration origins and repeated same origin | Two distinct origins have distinct IDs; the repeated origin has a stable ID; two registrations are indexed | `followup-probes.json`, `origins` |
| Recorder source drift | One capture gap; actual manifest recorded; hook observers stay inactive; native result unchanged | `followup-probes.json`, `source_drift_separate_fixture` |
| Host turn identity fixture | Entered and returned records retain first-turn and second-turn identities with the same session | `followup-probes.json`, `host_turn_identity` |
| Failed-only hook outcome | One terminal outcome, one failure, zero successes, zero interventions | `followup-probes.json`, `failed_hook_summary` |

The exact independent suite output is `local-tests.txt`. The suite includes detached parent exit, large native streams, duplicate positions, HTTP read limits, and selective thread capture context. The inherited follow-up probe source is preserved as `inherited-followup-probes.py`; its output is `followup-probes.json`. Its stderr contains exactly three expected recorder loss messages from deliberate NaN and cycle fixtures. Those are fixture measurements, not unexpected failures.

## Scope and side effects

This reviewer changed only files under this review directory. It made no implementation edits, commits, remote operations, Discord messages, or memory/journal calls. Synthetic files and loopback servers were removed by fixture cleanup. The reviewer invoked the existing 26-test suite, which includes its existing isolated startup fixture. The independent probes did not import Hermes bootstrap, install dependencies, build products, access production captures, or touch external systems.

Review hashes are preserved in `snapshot-before.json` and `snapshot-after.json`. This report verifies the reviewed source and the specific fixtures above. It does not certify later cookie or Basic corrections or deployment. The primary agent received both confirmed findings before this report was finalized.

## Required follow-up

The cookie and Basic corrections require failing regression evidence, a full suite run, and repeated independent fixture checks. Re-run `closure-probes.py` and `basic-probes.py` after those corrections. Cookie leak stages, Basic password leak stages, and Basic encoded leak stages must all become empty while the native outcomes remain unchanged. The current report is not an approval to deploy this source.
