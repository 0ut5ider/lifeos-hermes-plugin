# Authenticated owner PULSE API review

Date: 2026-10-01

Role: Independent code and behavior reviewer, Cerebo

Question: Does the new owner snapshot API bind real Hermes dashboard sessions to fresh installation policy, preserve governed native results, and return safe uncached outcomes across success and denial paths?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

The requested **35 tests pass independently in 17.922 seconds**, and the unchanged real localhost HTTP probe passes. Real owner authentication, account binding removal, root/configuration reload, and verified account isolation have positive evidence.

**Two bounded API defects remain:** corrupt registry errors escape the sanitized unavailable response, and host/framework-generated denials do not carry the promised `Cache-Control: no-store` header. Neither reproduction returned a private fact to an unauthorized caller.

Both findings were sent to the primary agent. Source capture finished before it began corrections. This report describes the frozen snapshot below.

## Reviewed snapshot

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

Branch: `feature/lifeos-memory`

HEAD: `c8ed5821e86b4fa838cff3f224c1be3242c5896a`, with working changes captured in `raw/working-diff.patch`.

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`

Owned sources:

- Hermes: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes`
- LifeOS: `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install`

| File | SHA-256 |
|---|---|
| Plugin `dashboard/plugin_api.py` | `9b2a767f8a5cd71de9b79303fcbfe66416a7a2abc3def2d6740e9112f9e60784` |
| `memory_preferences.py` | `c6fed71c732a1e305e0cca54f9b8523881e5a47e9055cceb953fad91bd84e9ab` |
| `test_memory_pulse_auth.py` | `08ae3cfb590d535a068728ba34c2640f26644b1359b14ab30523100e49945ed0` |
| Primary `probe_authenticated_routes.py` | `2ade56c6f1a3931fe73d40f99e822a630ec090bbd43718fb919795eafe5736c5` |
| Host `dashboard_auth/middleware.py` | `b2ca245bc151cbc955cead50234bdd9e5498f2a24e59d9e81d6f81cd8f7ea4b1` |
| Host `dashboard_auth/base.py` | `3e8bd7ac47e89afc461e649fd1dc38665660d9247daec113244bd8fa9e483773` |
| Host Basic provider `__init__.py` | `2c28412e323ae0ea6dcf119b9f453abae581178a4e4256ca92f33bb46a6273f1` |

All seven hashes remained unchanged through the review. Exact absolute paths and snapshots are in `raw/hashes-before.json`, `raw/hashes-after.json`, and `raw/sources/`. An initial capture command looked for `basic.py`; the provider is a package. The corrected package path and this command-only error are documented in `raw/capture-note.txt`.

## Finding 1: Corrupt registry escapes the safe unavailable response

Priority: Medium, availability and API contract.

The route catches `ValueError`, `OSError`, and `RuntimeError`, but the snapshot transaction can raise `sqlite3.Error`. A real synthetic registry corruption produces an uncaught `DatabaseError: file is not a database`.

Reproduction:

1. Create the ordinary synthetic owner fixture and log in through the real host password-login route.
2. Replace only that fixture's registry database bytes with an invalid synthetic payload.
3. Request the protected snapshot using the real authenticated client.

The standard test client propagates `DatabaseError`. With server exception propagation disabled, the actual ASGI response is:

```json
{"status":500,"cache_control":null,"body":"Internal Server Error"}
```

This differs from the route's intended sanitized 503 JSON unavailable result. No private configuration path or memory body appeared in the response, but callers receive an inconsistent error format and lack the cache directive.

Evidence: `raw/probe_errors.py`, `raw/errors.txt`. The probe uses the real database and native snapshot path. It does not replace the snapshot implementation.

Smallest correction: handle expected database availability exceptions at the HTTP boundary and map them to the existing generic unavailable envelope. Keep detailed internal errors out of the response. Add a real corrupt-registry route regression; separately evaluate expected native timeout exceptions if that boundary promises the same unavailable contract.

## Finding 2: Cache policy does not cover host and framework denials

Priority: Low, explicit response contract gap. No fact disclosure was measured.

The route sets `no-store` on responses it constructs. The host authentication middleware and FastAPI routing/validation can return before that function runs. Actual results are:

| Request | Status | Cache-Control |
|---|---:|---|
| Anonymous snapshot | 401 | absent |
| Invalid bearer with a valid cookie | 401 | absent |
| Unsupported view `graph` | 422 | absent |
| POST to snapshot | 405 | absent |
| Disallowed scope query | 400 | `no-store` |
| Valid owner snapshot | 200 | `no-store` |
| Removed owner account binding | 403 | `no-store` |

The same missing header appears after cookie logout, where the host returns 401. This is not evidence that a browser or proxy actually cached these responses; it means the explicit all-outcome no-store requirement is not implemented at the layer that sees those outcomes.

Evidence: `raw/errors.txt`, `raw/binding.txt`. The middleware denials use the actual prepared host gate and Basic provider.

Smallest correction: apply the protected-route cache policy at a response layer that includes authentication denials, method errors, and validation errors. Verify the actual middleware order. Avoid claiming a router-only response wrapper covers an earlier authentication short circuit.

## Verified behavior

### Real authentication and identity isolation

The tests and probes use the actual prepared Hermes `BasicAuthProvider`, password hashing, password-login route, cookies, and authentication middleware. Sessions are not fabricated.

Anonymous requests, arbitrary bearer strings, and caller identity headers fail. An invalid bearer does not fall back to a valid cookie. Disabling the host gate does not cause the endpoint to mint owner scope without a verified Session.

An additional control replaces the private fixture's provider with another real Basic account, logs that account in through password-login, and requests a snapshot with spoofed owner headers. The verified but unbound account receives 403 and no fact body.

The endpoint requires the host `Session` type, rather than the separate service `TokenPrincipal` type. The isolated app did not enroll a real noninteractive service token or mount the full host token-auth router. This review therefore establishes no authority from absent/invalid tokens and the source-level Session requirement, not a complete service-token integration proof.

### Fresh policy and root binding

The configuration is loaded per request and its installed root is checked before creating the owner scope. Same-connection account removal immediately returns 403. Binding the account to a different principal also fails. The requested tests cover root change denial without returning the private fixture path.

Independent controls confirm that public file permissions, malformed configuration JSON, and deleted configuration return sanitized 503 JSON with `no-store` and no fact body. These errors pass; the corrupt registry error described above does not.

### Logout and bearer semantics

Cookie logout removes browser cookie authority and the next cookie request receives 401. An already issued valid Basic bearer still receives 200 after cookie logout, consistent with this provider's stateless access-token semantics. Removing the account policy binding then makes that same bearer receive 403 immediately.

No server-side bearer revocation is claimed. The probe records only status, cache headers, and fact-presence booleans; it does not write access or refresh credentials to evidence.

### Fresh native data and transport

The unchanged primary network probe starts a private uvicorn server on an ephemeral localhost port and uses real httpx requests. All four owner views return 200 with `no-store` and no ETag. The current principal fact is visible, a governed forget makes the next snapshot count zero, account removal denies the next request, and cookie logout denies subsequent browser access.

Conditional owner requests with `If-None-Match` and `If-Modified-Since` receive a fresh 200 snapshot with `no-store`, not a stale 304.

The fixture mounts the actual auth components and plugin router in a FastAPI app. It does not run the complete Hermes dashboard or the native PULSE webserver.

## Commands and evidence

All commands run from the repository root with:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
```

`python` means the complete interpreter listed above.

```sh
python -m unittest test_memory_pulse_auth test_memory_dashboard test_memory_preferences test_memory_pulse -v
python docs/verification/2026-10-01-memory-pulse-http/probe_authenticated_routes.py
python docs/agents/2026-10-01-memory-pulse-auth-review/raw/probe_errors.py
python docs/agents/2026-10-01-memory-pulse-auth-review/raw/probe_binding.py
```

The exact detached suite command is in `raw/run_tests.sh`. `raw/tests.txt` contains all 35 passing outcomes and `raw/tests.done` records 0. Network output is `raw/network.txt`; new probe outputs are `raw/errors.txt` and `raw/binding.txt`. The error probe reports observed failures without assertion failure, so its zero process exit is not a passing correctness result.

## Limits and next review

Correct the two error-path gaps and rerun their unchanged probes plus the focused gate. Successful owner binding and data freshness do not close the full host dashboard mount, native HTTP relay, browser integration, delivery identity, broader lifecycle, or ownership activation.

No implementation, dependency, live configuration, account, or external system was changed. The temporary provider registrations, passwords, database changes, and localhost server belong only to isolated synthetic fixtures and were cleaned up. No live imports/bootstrap, SSH, memory tools, or journal tools were used.
