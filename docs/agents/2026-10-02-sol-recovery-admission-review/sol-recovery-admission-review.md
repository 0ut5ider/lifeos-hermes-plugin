Date: 2026-10-02
Role: Independent recovery admission reviewer
Question: Does befae76 safely close the recovery request admission gap against 1333713, while retaining authentication, owner authorization and valid caller behavior?
Model: GPT-6.1-Sol
Reasoning effort: high

Adrian, the recovery admission gap is closed. The affected route passes all 24 dashboard tests and 32 additional local HTTP scenarios. I found one P2 regression introduced by the synchronous route's conversion to an asynchronous route: recovery now performs its synchronous status and launch work on the server's event loop.

[P2] Keep synchronous recovery work off the event loop. The change at `lifeos_hook_bridge/dashboard/plugin_api.py:596` makes `recover_lifeos_update` asynchronous. After it awaits the guard, it calls `get_lifeos_update_status` and `_resume_lifeos_update` synchronously. The latter calls `_launch_lifeos_update`, which waits for `subprocess.run(..., timeout=30)` at line 543. Status inspection can also wait for `systemctl` for up to 15 seconds at lines 508-510. These waits previously ran in FastAPI's thread pool because recovery used a synchronous endpoint. They now delay other requests on the same event loop. The 15- and 30-second values are source timeouts, not measured production delays.

I reproduced the scheduling change against both exact commits with real loopback HTTP, real password authentication, and the real recovery route. The probe captures launch with a bounded local Python subprocess that sleeps for 0.8 seconds. It sends a concurrent request after launch starts. It does not run systemd or contact a remote service.

| Revision | Captured launch duration | Concurrent request duration | Concurrent request finishes during launch |
| --- | ---: | ---: | --- |
| Parent 1333713 | 0.8169 seconds | 0.0019 seconds | Yes |
| Reviewed befae76 | 0.8153 seconds | 0.8174 seconds | No |

Both recovery requests return 200. The failure is server responsiveness while synchronous recovery work runs. The report does not claim that a real launch normally takes 0.8 seconds. The measured comparison isolates the scheduling regression. Evidence and the complete probe are in `raw/scheduling-probe.txt`, `raw/scheduling-results.json`, and `raw/probe_recovery_scheduling.py`.

Keep the awaited admission guard. Run the prior synchronous recovery sequence, including status inspection, in `run_in_threadpool`. Keeping the sequence together also preserves its existing order and error handling. Add a focused concurrency regression that verifies another request can complete while the captured launch boundary waits. I made no implementation changes.

The guard executes before job status inspection, grant creation, job publication, or launch. The added regression tests all three original malformed request classes and checks request bytes, status bytes, grants, and launch calls after each rejection. Its recorded failing-before evidence calls launch three times and receives 409 from the synthetic launch exception. Separate primary before evidence records accepted 200 responses with fresh grants. Its after evidence records 403, 400, and 400 without grant or job changes. I preserved those primary records as attributed evidence; my independent tests run the reviewed commit.

The independent focused suite passes all 24 cases in 15.195 seconds with clean output and exit 0. This includes the added recovery admission regression, fresh recovery grants, owner revocation, retryable launch failure, and recovery when the live install directory is missing. The full output is `raw/dashboard-suite.txt`.

The 32 local HTTP scenarios use uvicorn bound to 127.0.0.1 and the actual Hermes password provider and gated authentication middleware. Of these, 29 reject the request and three accept it. They are component integration checks at a captured launch boundary, not an end-to-end worker claim.

The rejection checks cover anonymous requests with the host gate enabled and disabled, fabricated identity headers, an invalid bearer with a valid owner cookie, a revoked owner, and an authenticated account without an owner binding. They also cover other origins, null Origin, a changed scheme, five query forms, seven nonempty body forms, a chunked body, and GET, HEAD, PUT, PATCH, DELETE, and OPTIONS. Every rejection preserves watched request, status, snapshot, and configuration bytes and modes, creates no grant, and calls no launch. Expected responses are 401 for failed authentication, 403 for origin or owner denial, 400 for query parameters or nonempty bodies, and 405 for unsupported methods.

The accepted checks cover a current-origin POST without a body, a POST without Origin, and a zero-length POST with a JSON content type. Each returns 200 and captures exactly one launch with the current job and action `recover`. Its grant validates for the current owner, exact job, request digest, and recovery purpose. The validator refuses apply and restore actions, another job, a changed request, and mount purpose. Recovery scopes have no memory read or write categories. Grant and request files use mode 0600. Responses omit the grant path, and ownership remains disabled.

Authentication remains a dependency of the route. `_memory_account` accepts an actual Hermes `Session` from request state and derives the provider-qualified account. The admission guard receives no caller-selected account or job. The recovery job comes from the installed update root. The owner check and fresh grant creation remain in `_resume_lifeos_update` through the real preference and administration code. The tests verify these boundaries with actual authentication and authorization code.

The dashboard caller still sends `SDK.fetchJSON(recoverEndpoint, { method: "POST" })` without query parameters or a body. The pinned Hermes SDK preserves this request shape, includes credentials, and does not append its management profile to this plugin endpoint family. The three accepted local HTTP requests verify route compatibility with that shape. This review does not claim a browser click or a production reverse proxy test.

An initial review probe failed because I used nonexistent `MemoryScope.read_categories` and `write_categories` attributes. All its rejection scenarios had passed before that harness error. I corrected only the output-directory probe to use `read` and `write`, then reran it successfully. The initial log and partial data remain under `raw/initial-http-probe*`.

This review covers only the admission correction and affected caller. It does not reopen archive correction findings, repeat the previous 354-case Python, 32-case recorder, or 11-case dashboard gate, certify full memory behavior, certify hook parity, or approve release activation. Tests use disposable synthetic data. I did not change implementation, repository tests, configuration, or Git; deploy, activate, push, or contact remote services. The requested report, structured results, raw probes, source snapshots, command descriptions, and logs are saved in this directory.

The item that deserves review is R1: restore recovery's thread-pool scheduling while retaining the guard. Admission correctness and owner authorization pass within the stated component boundary. Real systemd launch, service restart, full memory behavior, and browser deployment behavior remain outside this review.
