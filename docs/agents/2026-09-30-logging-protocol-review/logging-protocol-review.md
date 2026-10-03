Date: 2026-09-30
Reviewer role: Independent logging protocol closure reviewer
Question: Do the Cookie and Basic authorization corrections remove declared credential echoes without changing native hook behavior, and do realistic nearby cases expose another blocker?
Model: GPT-6 via Codex, inherited from the primary agent. The harness does not expose a more specific service model identifier.

## Decision and reviewed source

The single-cookie and Basic authorization corrections pass independent real hook reproducers, and all 28 tests pass locally in 6.275 seconds. A nearby real HTTP fixture confirms a remaining credential leak when a response sends multiple Set-Cookie headers. This finding blocks closure for the reviewed source.

The protocol corrections are present in commit `7e2b57e` according to the primary agent. This reviewer first reads the corrected working tree while HEAD is `8de64ff`, then observes HEAD `dd9e7d50430f8f60ad8e64dee6f739803a310f1d`. Source identities from the actual captured process are authoritative for the probes because the primary agent commits concurrently. These captured hashes appear in `multiple-cookie-probes-confirmed.json`:

| Recorder file | SHA-256 |
| --- | --- |
| `store.py` | `793f9971ce99ab2f2e3269eef172c1560bcd04004db01542593812ffb51fa09b` |
| `instrument.py` | `d13042fdb5775059ed070f5597894625345cbfd917782143164651b14b9dd90d` |
| `analysis.py` | `6d2d23be5778b99976018fab81597fec905fda2f3d490c41afc22e3720779dc4` |

## Confirmed blocker

### P1: Repeated Set-Cookie response headers lose a declaration before echo filtering

Location: `development/hook_capture/instrument.py`, `patch_http.Response.read`, the conversion `dict(response.headers)` passed to `http.response_read`.

The real local HTTP fixture sends two distinct Set-Cookie fields:

```text
Set-Cookie: session=SYNTHETIC-CLOSURE-COOKIE-192837; HttpOnly; Path=/
Set-Cookie: access=SYNTHETIC-SECOND-COOKIE-837291; HttpOnly; Path=/
```

The response body contains ordinary echo fields for both values. The recorder's HTTP header conversion collapses the repeated name before credential discovery. It retains the first cookie declaration and loses the second. The new SimpleCookie discovery code correctly learns the value of the declaration it receives, but it never receives the second declaration.

The independent fixture reports no leak stages for the first cookie. The second cookie remains in six stages: `http.response_read`, `run_http.returned`, `hook.completed`, `response.parsed.entered`, `response.parsed.returned`, and `translation.returned`. The stored http.response_read header is redacted, which can make a superficial check appear successful while the decoded byte body still exposes the second cookie. The fixture captures 19 events and reports an unchanged native versus traced outcome.

This is a repeatable loss of an explicitly supported HTTP credential declaration. Multiple cookies in one HTTP response are an ordinary case. The finding does not require recognition of an unrelated encoding or an unknown authentication scheme.

The smallest correction preserves all response header values in the stored representation before discovery, for example, a mapping from each header name to a list of its observed values. The existing declared_secrets list traversal already preserves the field key and can parse each Set-Cookie value. Keep the native response object and read operation unchanged. Verify both echoed values with a real HTTP regression that expands stored base64 bodies.

The primary agent received this finding promptly. This report does not certify a later implementation correction. The exact captured artifacts and source hashes are preserved so that a repeat run can distinguish the original defect from later fixes.

## Independently verified corrections

| Check | Result | Raw evidence |
| --- | --- | --- |
| Complete existing suite | 28 tests pass in 6.275 seconds | `local-tests.txt` |
| Single Set-Cookie declaration and body echo | No leak stages; native outcome unchanged; declaring header redacted | `closure-probes.json`, `real_cookie_http_hook` |
| Basic declaration, bare password echo, encoded token echo | Both leak stage lists empty; native outcome unchanged | `basic-probes.json` |
| Bearer declaration and bare token echo | No leak stages; native outcome unchanged | `closure-probes.json`, `real_bearer_hook` |
| Valid and invalid artifact references in either order | One artifact error; valid inventory contributes one registration in either order | `closure-probes.json`, `reference_orders` |
| Invalid artifact reference to an inventory | One artifact error; no registration added from invalid inventory | `closure-probes.json`, `invalid_reference_cannot_index` |

The script copies `closure-probes.py` and `basic-probes.py` into this new review directory before execution. Their original review sources and outputs remain intact. `multiple-cookie-probes.py` changes the single-cookie HTTP fixture to send a second Set-Cookie header and echo both values. It records separate first-cookie and second-cookie leak lists and captures actual recorder source hashes from the process.initialized artifact.

Raw evidence files:

| File | Contents |
| --- | --- |
| `closure-probes.py`, `basic-probes.py` | Copies of the previous review's reproducible fixtures. |
| `closure-probes.json`, `basic-probes.json` | Current source results for the requested real probes. |
| `multiple-cookie-probes.py` | Additional real HTTP fixture and synthetic artifact exporter. |
| `multiple-cookie-probes.json` | First multiple-cookie reproduction. |
| `multiple-cookie-probes-confirmed.json` | Repeated reproduction, per-cookie leak lists, and actual source hashes. |
| `multiple-cookie-artifacts.json` | Synthetic event records and expanded artifacts from the repeated reproduction. |
| `*-stderr.txt` | Empty probe stderr streams. |

Reproduce from the checkout:

```bash
python3 -m unittest discover -s development/tests -v
python3 docs/agents/2026-09-30-logging-protocol-review/closure-probes.py
python3 docs/agents/2026-09-30-logging-protocol-review/basic-probes.py
python3 docs/agents/2026-09-30-logging-protocol-review/multiple-cookie-probes.py
```

The last command writes the synthetic artifact export inside this review directory. Preserve the existing file under another name before rerunning it against a correction.

## Supported protocol limits and review scope

The new component discovery code recognizes Cookie and Set-Cookie fields through SimpleCookie, and recognizes Basic values under Authorization and Proxy-Authorization with validated base64 and UTF-8 decoding. It also retains the existing Bearer and credential-field filtering. Unknown authorization schemes, malformed or unrecognized cookie syntax, unrelated encodings, and arbitrary prose remain outside a comprehensive sanitizer guarantee. This review does not expand that support into a general credential detection project.

The verified native comparisons use unchanged bridge code, actual command processes, and a real loopback HTTP server. They establish the observed behavior in these fixtures. They do not establish every native hook's semantic behavior, all deployment paths, historic artifact safety, or comparative latency.

This reviewer made no implementation edits, commits, pushes, remote actions, service changes, account configuration changes, Discord messages, bootstrap imports, builds, memory calls, or journal calls. It wrote only this review directory. The primary agent made implementation and documentation changes concurrently. All credentials, body values, and artifacts in this report are synthetic.

## Required closure check

Correct the repeated-header capture boundary, add a real regression, and rerun the multiple-cookie fixture. Both first-cookie and second-cookie leak stage lists must become empty while native outcomes remain unchanged. Verify the full suite and identify the corrected source before deploying the reviewed recorder. The single-cookie and Basic passing probes do not close this repeated-header case.
