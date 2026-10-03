Date: 2026-10-02
Role: Independent scheduling closure reviewer
Question: Does 2ef78f3 close the event loop scheduling regression against befae76 while preserving recovery admission, owner authorization and error mapping?
Model: GPT-6.1-Sol
Reasoning effort: high

Adrian, the scheduling finding is closed. I found no material issue introduced by this correction within the requested recovery route and immediate caller contract. All 25 dashboard component cases and all 32 additional local HTTP admission scenarios pass.

The route at `lifeos_hook_bridge/dashboard/plugin_api.py:596` retains its authentication dependency and awaited request guard. It then awaits the existing Starlette `run_in_threadpool` implementation with `_recover_lifeos_update` and the verified account string. The helper contains the complete prior synchronous sequence, including status inspection, job selection, owner grant creation, job publication and launch. An AST comparison confirms its body matches the previous route body after the admission guard. The authentication, request guard, status inspection and resume functions are also unchanged. The installed Starlette implementation awaits AnyIO's thread runner and returns its result.

I independently repeated the scheduling probe against both exact commits. The probe runs uvicorn on 127.0.0.1, authenticates with the real password provider and calls the real recovery route. It captures launch with a local Python subprocess that sleeps for 0.8 seconds. It sends an unrelated request after launch starts. It does not invoke systemd, restart a service or contact a remote system.

| Revision | Captured local launch | Concurrent request | Request finishes during launch |
| --- | ---: | ---: | --- |
| befae76 before correction | 815.97 ms | 818.16 ms | No |
| 2ef78f3 reviewed correction | 816.48 ms | 1.80 ms | Yes |

Both recovery requests return 200. This comparison reproduces the prior event loop block and demonstrates that the correction removes it at the captured launch boundary. These numbers describe a synthetic local wait. They do not estimate real systemd launch time. Complete source snapshots, the probe and measurements are in `raw/probe_recovery_scheduling.py`, `raw/scheduling-probe.txt` and `raw/scheduling-results.json`.

The existing dashboard suite passes all 25 cases in 15.719 seconds with clean output and exit 0. The added concurrency regression waits for launch to enter, requests another route and verifies that launch has not finished when that response arrives. Its launch release occurs in a `finally` block. The suite also verifies fresh recovery authority, revoked owner rejection, missing live installation recovery, and launch failure mapping to 409 while preserving retryable job bytes and revoking the grant. Raw output is `raw/dashboard-suite.txt`.

The independent admission probe passes 32 scenarios with real loopback HTTP, authentication middleware, password sessions, owner configuration and grant validation. Launch is captured locally. The 29 rejections preserve watched request, status, snapshot and configuration bytes and modes, create no grant and make no launch call. They cover anonymous requests with the host gate enabled or disabled, fabricated identity headers, an invalid bearer with an owner cookie, a revoked owner, an authenticated unbound account, other origins, query parameters, nonempty bodies including chunked input, and unsupported methods. Responses preserve the expected 401, 403, 400 and 405 mappings.

The three valid forms, current Origin without a body, no Origin without a body, and zero-length JSON content type, each return 200 and capture one recovery launch for the current job. The grant validates for the verified owner, exact job, request digest and recovery purpose. Validation refuses apply, restore, another job, another request and mount purpose. Recovery authority has no memory read or write categories. Request and grant files use mode 0600. The response omits the grant path, and ownership remains disabled. The raw cases, responses and state hashes are in `raw/http-probe-results.json` and `raw/http-probe.txt`.

The dashboard caller continues to send a POST without query parameters or a body through `SDK.fetchJSON(lifeosUpdateEndpoint + "/recover", { method: "POST" })`. The saved snippet is `raw/caller-recovery-snippet.txt`. The accepted HTTP cases cover this route request shape. This review does not claim a browser interaction or production proxy test.

HEAD and both changed files match commit 2ef78f30305e891659086dd751962ea65e56c390 before and after validation. The comparison base is befae76f1770282ab568bb1908b7d635d5f06a2f. Source hashes, the patch, semantic comparison, command script, exit markers and logs are saved under `raw/`; structured conclusions are in `data.json`. The probes adapt the previous admission review's scripts and save new outputs here. I did not overwrite prior evidence.

I changed only review artifacts in this directory and used disposable synthetic fixtures. I made no implementation or repository test edits, Git mutations, deployment, configuration activation or ownership activation. No memory or journal calls, delegation or external service access occurred. Validation is complete, and no further source reads or tests are running for this review.

The remaining verification limit for Adrian's review is the captured launch boundary. Real systemd execution, service restart, full memory behavior and unrelated release acceptance remain outside this bounded closure review. No new inherited issue requires a decision here, and this report does not recertify historical acceptance items.
