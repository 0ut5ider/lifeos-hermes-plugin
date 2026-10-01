# Authenticated PULSE API closure review

Date: 2026-10-01

Role: Independent code and behavior reviewer, Cerebo

Question: Do the response-header and expected-error corrections close the two API findings, including actual owned-host mounting, without changing credential binding or unrelated responses?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

**Both reproduced API findings are closed. No new material finding was identified in this bounded review.** The independent focused gate passes **38 tests in 20.273 seconds**. The unchanged error, binding, and real HTTP probes pass. The actual owned-host mount probe also passes.

Additional concurrent ASGI controls verify that the middleware applies to the intended prefix, handles a deployment root path, preserves unrelated responses, removes validators from protected responses, and installs only once.

This closes the bounded authenticated Hermes owner snapshot API review. Native relay, browser integration, full delivery/lifecycle coverage, and ownership activation remain open.

## Reviewed snapshot

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

Branch: `feature/lifeos-memory`

HEAD: `c8ed5821e86b4fa838cff3f224c1be3242c5896a`, plus reviewed working changes.

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Owned prepared sources:

- Hermes: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes`
- LifeOS: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

| File | SHA-256 |
|---|---|
| Plugin `dashboard/plugin_api.py` | `2f373e78d37b7e99b801580d5a04f579e58a66a25de24980bd867c2971afe0b5` |
| `memory_preferences.py` | `c6fed71c732a1e305e0cca54f9b8523881e5a47e9055cceb953fad91bd84e9ab` |
| `test_memory_pulse_auth.py` | `d4484e2ee4e2aacac496f8bb6be779b5e957673f3aed9cbd8dc2c1c83049eddd` |
| `probe_authenticated_routes.py` | `2ade56c6f1a3931fe73d40f99e822a630ec090bbd43718fb919795eafe5736c5` |
| Host auth middleware | `b2ca245bc151cbc955cead50234bdd9e5498f2a24e59d9e81d6f81cd8f7ea4b1` |
| Host auth base | `3e8bd7ac47e89afc461e649fd1dc38665660d9247daec113244bd8fa9e483773` |
| Host Basic provider | `2c28412e323ae0ea6dcf119b9f453abae581178a4e4256ca92f33bb46a6273f1` |
| `probe_host_mount.py` | `d1d1abebf8bbeb5b63a9e2de7670afcc5bfe992509ccd3ef3dd8cee1d310668a` |

All eight hashes remained identical before and after the tests and probes. Exact absolute paths are recorded in `raw/hashes-before.json` and `raw/hashes-after.json`. Source copies are in `raw/sources/`; `raw/hash-check.txt` records stability.

## Findings verified closed

### Corrupt registry becomes a sanitized unavailable result

The unchanged `probe_errors.py` again corrupts only the synthetic fixture registry and requests a snapshot through real host authentication. It now receives:

```json
{
  "status": 503,
  "cache_control": "no-store",
  "body": "{\"error\":\"Memory is unavailable under the current installation policy\"}",
  "etag_present": false
}
```

The previous uncaught `DatabaseError` is absent. The endpoint catches expected SQLite errors and returns the existing generic unavailable envelope. It also explicitly catches native subprocess timeout errors; this review inspected that branch but did not force an actual timeout.

Evidence: `raw/errors.txt`, unchanged original script recorded in `raw/probe-results.json`.

### Host and framework denials receive the cache policy

The same unchanged probe confirms `Cache-Control: no-store` on:

- Anonymous 401.
- Invalid-bearer 401, including the valid-cookie control.
- Unsupported-view 422.
- Unsupported-method 405.
- Disallowed-query 400.
- Corrupt-registry 503.

The endpoint still adds the header directly to its own envelopes. The pure ASGI middleware adds it to early host authentication and framework responses for the protected prefix.

The middleware does not store per-request state on its instance. Its path and send wrapper are local to each call. It replaces cache directives and strips ETag and Last-Modified only from matching HTTP responses.

## Actual host mounting

The unchanged primary mount probe uses a synthetic HOME and Hermes profile, links the plugin into that private profile, and imports the real owned public `hermes_cli.web_server`. It runs the actual app lifespan and real Basic password authentication.

Observed results:

| Operation | Status | Cache-Control |
|---|---:|---|
| Anonymous snapshot | 401 | `no-store` |
| Authenticated owner snapshot | 200 | `no-store` |
| Invalid view | 422 | `no-store` |
| Invalid method | 405 | `no-store` |

The plugin detects the already-loaded host module and app during assembly. It installs its middleware before startup without importing or bootstrapping a host itself. The probe asserts the installation flag and verifies one current synthetic fact. No Hermes patch is required for this path.

Evidence: `raw/host-mount.txt`, `raw/host-mount-stderr.txt`, and the exact command in `raw/probe-results.json`.

The host emits its expected warning about linked SQLite 3.51.2 and its journal-mode fallback. The complete original output remains intact, and the warning is also saved separately in `raw/host-warning.txt`. No interpreter, dependency, or database setting was changed to suppress it. This is an observed environment warning, not a clean-output claim or a newly introduced API defect.

## Concurrency, prefix, and isolation controls

`raw/probe_headers.py` uses the real exported installation helper on a separate synthetic FastAPI response app. It sends 40 concurrent ASGI requests across the normal root and `/deployment` root path. Half target the protected prefix; half target the adjacent `memory/pulsex/` path.

The protected responses receive exactly the no-store cache directive and lose ETag and Last-Modified. Adjacent-path responses retain their public cache directive and both validators. An unrelated header and each request's unique synthetic tag remain correct, showing no response mixing. Installing the helper twice creates one middleware entry.

This is a middleware behavior control using synthetic public response bodies. It does not fabricate authenticated Sessions or substitute for the real authentication and network probes.

The first version of this probe tried to locate a flattened route in the app route list and stopped before making requests. It was corrected to retrieve the exported helper from the installed middleware class. The fixture-only failure remains in `raw/headers-fixture-error.txt`; the successful output is `raw/headers.txt`.

## Preserved owner binding and data freshness

The unchanged real network probe verifies all four owner views, current native fact visibility, fresh forget results, immediate account-binding removal, and cookie logout. All pass.

The unchanged identity/configuration probe verifies:

- A different genuinely authenticated Basic account receives 403 despite owner-spoofing headers.
- Missing, malformed, and nonprivate configuration returns sanitized 503 with no-store.
- Conditional owner requests receive fresh 200 responses.
- Cookie logout removes cookie authority.
- An issued stateless Basic bearer remains valid after cookie logout.
- Removing the account binding immediately denies that same bearer.

No server-side bearer revocation is claimed. The tests record outcomes without persisting session credentials. Existing policy/root binding behavior is unchanged in this correction.

## Commands and evidence

All commands ran from the repository root with:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
```

`python` below refers to the complete interpreter listed above.

```sh
python -m unittest test_memory_pulse_auth test_memory_dashboard test_memory_preferences test_memory_pulse -v
python docs/agents/2026-10-01-memory-pulse-auth-review/raw/probe_errors.py
python docs/agents/2026-10-01-memory-pulse-auth-review/raw/probe_binding.py
python docs/verification/2026-10-01-memory-pulse-http/probe_authenticated_routes.py
python docs/verification/2026-10-01-memory-pulse-http/probe_host_mount.py
python docs/agents/2026-10-01-memory-pulse-auth-review/final-closure/raw/probe_headers.py
```

`raw/run_tests.sh` records the exact detached test command. `raw/tests.txt` contains all 38 passing outcomes, and `raw/tests.done` is 0. `raw/probe-results.json` contains exact interpreter commands and successful return codes for the four archived probes. Their stdout and stderr are preserved separately. The error probe reports values without asserting all expected outcomes; those values were inspected directly.

## Scope and handoff

The concrete error and cache findings are closed with independent evidence. This review supports the startup mounting contract for the owned host source used here. It does not approve a native PULSE relay, browser behavior, all service-token integrations, general delivery identity, full lifecycle, or ownership activation.

Only the evidence directory and disposable synthetic fixtures were written. No implementation, live account, configuration, dependency, or external system was changed. No live fleet imports/bootstrap, SSH, memory tools, or journal tools were used.
