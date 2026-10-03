Date: 2026-10-01
Agent role: Independent reviewer, bounded next-gate design opinion
Question: Which per-request authentication boundary should govern native PULSE memory while preserving useful authorized owner access?
Model: GPT-6.1-Sol, high reasoning effort (inherited from parent)

# Native PULSE memory request identity

Adrian, implement a narrow authenticated Hermes memory-response proxy for the next gate. Reuse the existing owner dashboard authentication and governed memory service. In managed mode, PULSE must obtain authority from the credentials on each actual HTTP request, not its process environment. An unauthenticated request gets no hot entries, proposals, diagnostic samples, run labels, or state snapshot, even when PULSE runs inside an owner agent environment.

Do not create a separate PULSE owner bootstrap session for this gate. A second browser credential would add issuer, expiry, logout, revocation, signing-key, cookie, and recovery behavior to maintain. The existing authenticated owner interface is the sufficient authority boundary. Preserve native response shapes and useful owner results by putting the governed snapshot behind that boundary, then adapt the native browser caller to use it. A proxy endpoint alone does not prove the native browser remains usable; origin, path prefix, cookie/token handling, and the actual frontend request must pass the network gate below.

## Evidence and limits

I inspected code and documents only. No runtime, server, bootstrap, package, dependency, model, SSH, memory, or journal operation ran. No configuration or implementation changed. The only writes are this report and its source artifacts.

The local plugin HEAD read during the review is `8970c41d321f7c7b57a5b702d521853994d95db2`. Current source bytes are pinned in `raw/sources.json`. Native source is the owned prepared tree under `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-closure/lifeos/LifeOS/install/LIFEOS/PULSE/`. I did not claim that this prepared tree is an unpatched upstream release. The archived Hermes authentication files are earlier review artifacts, not a fresh runtime inspection; they support the proposed reuse path but cannot establish current host logout, revocation, cookie scope, or optional-auth behavior.

`MemoryConfiguration` is a class in `lifeos_hook_bridge/memory_service.py:93`, not a separate `memory_configuration.py` file. A read of the guessed filename failed. A guessed native `frontend/` directory also did not exist; actual source frontend files are under `PULSE/Observability/src/`.

## Concrete observations

| Source | Observation | Implication |
| --- | --- | --- |
| `PULSE/pulse.ts:808-824` | Bun serves a separate listener. Its default loopback binding and Host check precede route dispatch. | Neither loopback nor Host establishes a memory principal. A local HTTP client can send a valid Host. |
| `PULSE/pulse.ts:946-950` | The memory module receives the current Request and pathname. | There is a suitable request boundary; no daemon-global identity handoff is necessary. |
| `PULSE/modules/memory.ts:253-290` | The handler checks only method/path, then reads local files and returns JSON. | It does not presently authenticate its caller or reload a governed request scope. |
| `PULSE/modules/memory.ts:83-203` | Helpers read JSON, JSONL, hot entries, directory names, and dispatch logs. | Authorization must precede those reads; filtering only the final JSON would leave a direct-reader bypass. |
| `PULSE/modules/memory.ts:206-250` | Full snapshot includes cadence, state, health, proposal samples, hot content, fire samples, and run item filenames. | A safe snapshot must govern all fields, including labels and nested historical strings. Protecting only hot entries is insufficient. |
| `memory_preferences.py:30-34,59-66` | Preferences reload configuration and verify installation root; owner review uses a trusted dashboard scope. | Reuse this pattern after HTTP authentication, rather than fabricate an ambient owner SessionContext. |
| `memory_service.py:128-136,178-194,245-282` | Configuration loads validate private permissions; context/client calls reload configuration and resolve their authority. | A per-request owner endpoint can reuse current policy/root checks. Passing an old MemoryScope to `call()` alone does not freshly resolve its authority. |
| `dashboard/plugin_api.py:52-88` | Plugin owner endpoints delegate to MemoryPreferences; handler functions themselves do not establish identity. | Their safety relies on the Hermes dashboard boundary. The new endpoint must stay behind that boundary and must not be added to public paths. |
| `memory_sharing.py:104-166` | External grants use restricted, fixed-identity SSH commands and reloadable client policy. | These grants do not provide a browser/PULSE owner credential. Keep MCP sharing separate. |
| `dashboard/dist/index.js:18,40-58` | Existing plugin UI uses `SDK.fetchJSON` for protected owner API requests. | Reuse the supported dashboard client path when rendering an owner view there. Never export its daemon or administration token as a general PULSE configuration value. |
| `PULSE/Observability/src/lib/local-api.ts:1-19` | Native API helper fetches relative paths; no plugin identity exchange is visible. | Different port/origin and dashboard path-prefix handling need an explicit integration. |
| `PULSE/Observability/src/app/memory/page.tsx:12-13` | `/memory` redirects to `/memory/knowledge`. | Do not assume this is a consumer of the four snapshot endpoints. |
| `PULSE/Observability/src/app/memory/graph/page.tsx:99` and `pulse.ts:1034-1041` | Graph requests `/api/memory/graph`, which the four-route snapshot module does not handle; the listener can fall through to Observability. | This next gate must name its exact route coverage. Protecting four snapshots does not establish security of graph/wiki/all PULSE. |

Searches of the inspected frontend source found no `principalMemory`, `daMemory`, `cadenceConfig`, `proposalsRecent`, or `recentRuns` consumer. Therefore preserving the snapshot schema is a compatibility requirement, not proof of an existing visible snapshot panel. Locate the actual enabled consumer before claiming native UI parity. The graph caller is a separate observed consumer with a separate reader path.

## Recommended boundary and request flow

1. Add an exact, read-only owner endpoint to the existing authenticated Hermes plugin router, for example `/api/plugins/lifeos-hook-bridge/memory/pulse/{snapshot|state|health|runs}`. Use an explicit enum/allowlist, not a generic URL or filesystem proxy.
2. Hermes authenticates the actual request using its existing dashboard authentication. Where the host supports multiple authenticated accounts, only its established installation-owner authority is sufficient; authentication as an arbitrary account must not mint owner scope. If the selected dashboard authentication mode is unavailable or disabled, this endpoint must refuse owner data rather than treat arrival as proof.
3. The endpoint reloads MemoryConfiguration for each request, verifies the installation binding, and constructs owner read authority from that current configuration after host authentication. It calls one governed projection implementation. Native facts remain authoritative; no snapshot archive, cached fact store, or new extraction process is introduced.
4. The governed implementation reads permitted hot memory and proposal results through existing operations. It authorizes diagnostic/source evidence before body or run-directory reads, then filters retired claims and labels using the existing retirement rules. It returns the same useful native fields and operational semantics. Missing source fields retain native partial-data behavior, while authentication, configuration, or connector failure returns explicit unavailable/unauthorized status, not a successful empty-memory claim.
5. In managed PULSE, intercept each of the four exact native `/api/memory` routes before existing raw helpers. Delegate to the fixed authenticated Hermes endpoint using only the credentials presented on that incoming Request. Strip untrusted owner/scope/caller/context headers. Do not fill missing credentials from `LIFEOS_MEMORY_CONTEXT`, a startup owner scope, a dashboard daemon token, or a persistent service credential. The native module forwards the governed response and performs no local memory-body reads in this branch.
6. A successful server-to-server proxy check must authenticate the originating caller, not merely PULSE as a process. Forward only the host's supported request credential fields to the fixed trusted Hermes origin. Never forward credentials to a caller-specified host, redirect, or arbitrary proxy path. Refuse redirects. Preserve verified authentication failure instead of trying native fallback. The server must not accept a spoofed forwarded-identity header in place of its usual authentication.
7. Wire the real native owner browser caller to the existing authenticated endpoint. When it runs inside the Hermes dashboard, use its SDK and configured host prefix. When it remains on PULSE's separate origin, call the fixed protected Hermes URL with the supported owner session, strict configured-origin handling, and explicit credential behavior. Do not assume dashboard cookies are sent to PULSE: cookies ignore ports but still obey host, path, Secure, and SameSite rules. The native relay can preserve clients that already present valid credentials, but cannot invent missing ones. A missing/expired session should offer the existing Hermes sign-in flow and show unavailable memory.
8. Keep genuinely unmanaged standalone LifeOS behavior in its separate branch. Once this installation is declared managed, missing or broken connector/authentication must never select the unmanaged raw reader. Managed detection must come from installation configuration or the existing trusted connector setup, not from the presence of per-request context.

The browser integration should use the shortest supported owner path in this compatibility set. Prefer the existing dashboard SDK where a native owner view is hosted there. For a separate native origin, first prove that the existing authenticated endpoint can receive and validate its owner credentials. Configure narrowly allowed browser origin access if needed; do not enable wildcard credentialed CORS or copy an admin bearer into native page JavaScript. If that owner session path is unsupported by the pinned host, report the missing browser contract and review that specific extension. Do not quietly replace the native UI with a static disabled page or assume a cookie bootstrap solved logout.

This recommendation is an authenticated memory response proxy, not a full PULSE reverse proxy. It does not route unrelated PULSE control APIs through owner authority, accept generic upstream URLs, or expose native administration as an MCP permission.

## Minimal implementation footprint

| File/group | Required change |
| --- | --- |
| `lifeos_hook_bridge/dashboard/plugin_api.py` | Four exact authenticated read routes, request/auth failure behavior, controlled response headers. Reuse existing host owner authentication. |
| `lifeos_hook_bridge/memory_preferences.py` | Owner snapshot entry point that reloads configuration and verifies the installed root each time. Owner authority is minted only after the router's authentication boundary. |
| One plugin module such as `memory_pulse.py`, with the smallest necessary MemoryService/source interface extension | Govern native snapshot fields, sources, run directories, and retirement filtering once. Preserve operational fields and enforce explicit unavailable outcomes. Avoid a second fact store or a global owner-context cache. |
| Native memory patch: `PULSE/modules/memory.ts`, and `pulse.ts` only if dispatch must enforce the boundary | Managed request delegation; exact path/method handling; no raw fallback. Keep unmanaged native branch intact. |
| Actual native frontend caller/helper | Adapt only memory requests to the authenticated owner path and correct dashboard prefix/origin. Preserve the native view and field semantics. The current graph helper must not be mistaken for a four-snapshot caller. |
| Focused tests plus existing native patch preparation/evidence records | Real network authority cases, governed snapshot fixtures, and exact distributed source reproduction. |

Do not add a package by default. Existing Python HTTP/FastAPI facilities and Bun fetch cover the transport. Authentication uses the host's maintained implementation. Snapshot reads and filters reuse the plugin's existing governed memory implementation. A new dependency requires a demonstrated missing facility, not a guess.

## Revocation, CSRF, cache, and scope requirements

**Revocation:** Verify host authentication on every HTTP request. A host logout, session revocation, or expired credential must stop subsequent requests using the existing connection. Reload memory configuration/root/owner binding each time. Pending requests authenticated before a revocation need a documented authorization point; do not promise retrospective removal of already returned data. This path must not keep a long-lived independent PULSE session whose five-minute expiry becomes a substitute for revocation. The earlier host-auth source artifacts do not prove immediate revocation in every currently configured host provider, so include the actual provider mode in evidence.

**CSRF and browser origins:** Keep these endpoints read-only GET with no ownership/grant/proposal mutation. Reject non-read methods explicitly. Sensitive responses must not have permissive cross-origin headers. Separate-origin native UI access requires an exact configured trusted origin and browser tests; it cannot use Origin as authentication. If the route ever gains a state-changing operation, use the host's CSRF protection and explicit owner action; that change is outside this next read-only gate. Do not let refresh/login redirects turn the proxy into an untrusted-origin credential flow.

**Caching:** Set `Cache-Control: no-store` on governed and denied memory responses, including the native relay; avoid ETag/304 reuse for this gate. Do not cache an owner snapshot globally in PULSE or return stale success on upstream failure. Frontend query caches must discard sensitive values after 401/403, logout, principal/root/policy changes, and retirements; authentication rechecks are still required for every fetch. Nothing can recall a response already downloaded, so do not claim client-copy erasure. If caching is added later, it needs authenticated identity, policy/root revision, and fact-generation invalidation.

**Scope:** The native operational snapshot is an installation-owner read surface, not an external-client read category grant. An SSH client with project access cannot gain it by naming itself owner. The owner view can show native operational fields and permitted records; historical proposal/run samples still pass retirement and physical-source policy. This does not grant proposal approval, automatic review, memory ownership activation, or arbitrary native file reads. Add no HTTP enrollment/token registry to MemoryConfiguration for this path.

## Actual network acceptance gate

Run these after implementation using disposable LifeOS/Hermes roots and synthetic files. This review did not run them.

1. Start the actual isolated Hermes authenticated dashboard and the actual patched PULSE listener on separate localhost ports. Use the pinned host authentication mode and native distributed source. Confirm exact revisions and configuration paths.
2. Call all four PULSE snapshot endpoints anonymously while the PULSE process has an owner-looking `LIFEOS_MEMORY_CONTEXT`. Repeat with no context and a fabricated owner header. All calls must refuse without reading protected snapshot sources or exposing synthetic markers, filenames, counts, or proposal samples.
3. Authenticate an owner through the actual supported dashboard flow. Call all four endpoints through the intended browser/proxy path. Verify native response fields, hot entries, cadence, health, proposal/run samples, and missing-source partial behavior. Use real HTTP requests, not only mocked service calls.
4. Interleave an owner request and an anonymous/restricted request concurrently in the same PULSE process. Verify one request's identity cannot overwrite process context or authorize the other. Test present-but-invalid credentials without fallback.
5. Change the owner binding, configuration root, permissions, and current fact retirement state between two requests on the same keep-alive connection. Verify fresh configuration, source boundaries, and excluded claims. Revoke/log out the host session and verify the next request cannot reuse cached authority or JSON.
6. Make the Hermes auth provider unavailable, stop the authenticated endpoint, and break connector configuration. Preserve explicit failure and no raw fallback. Exercise missing/expired credentials, redirects, wrong endpoint origin, unexpected path/method, malformed response, timeout, and oversized bounded response behavior.
7. Use the actual browser owner entry. Verify URL prefixes, exact cookie/credential behavior, denied cross-origin reads, no credential in query strings/history/referrers/logged page data, and UI clearing after authorization failure. A localhost HTTP client success alone does not prove browser usability. Browser login and refresh behavior must use the selected host contract.
8. Run an unmanaged synthetic native control and compare operational fields/results with managed authorized output after expected retirement filtering. Check standalone fallback separation and the registered patch preparation path.
9. Record unsupported graph/wiki/other PULSE source routes separately. Do not mark the whole listener or entire memory UI covered by the four-route result. The already observed `/api/memory/graph` path needs its own governed reader/identity work before a broad memory-UI or ownership claim.

The dependency order is governed snapshot semantics, host-authenticated owner API, native managed relay, actual frontend integration, then revocation/concurrency/browser network cases. The broader ownership and release gates remain open.

## Why the cookie/bootstrap alternative is not the next choice

A one-time, short-lived bootstrap credential and HttpOnly cookie can preserve a native origin without forwarding host credentials, but it is still a second authentication lifecycle. It needs owner-authenticated issuance, replay prevention, principal/root binding, secure storage/signing, cookie scope and transport policy, CSRF, active revocation, logout propagation, restart invalidation, and fresh policy resolution on every read. A signed short-lived cookie alone establishes neither fresh owner binding nor active revocation. An in-memory token table avoids a durable registry but still requires issuer/consumer coordination and restart behavior. These are new implementation responsibilities despite the small code footprint of issuing a token.

If network/browser evidence proves the current host cannot support the proxy's native owner path, revisit that bounded session bridge with explicit logout and revocation evidence. Do not add it preemptively as a workaround for an unauthenticated raw endpoint.

## Authorization and review decision

This narrow per-request authenticated memory projection implements the already approved governed access design and preserves the accepted single-store ownership model. It does not need a new architectural choice from Adrian before the primary makes it concrete in disposable fixtures. The host owns authentication, the plugin owns governed memory projection, and native PULSE owns its UI/native operational view.

Exposing a new public PULSE listener, adding a persistent HTTP client-grant system, reverse-proxying the entire PULSE administration surface, or replacing host authentication would change architecture or external policy and need a separate decision. This recommendation does none of those things. It identifies the frontend origin/auth path as a required compatibility check rather than treating loopback or ambient agent identity as permission.

The next implementation unit is ready to specify as: governed owner snapshots served by an authenticated Hermes request boundary, native PULSE delegation bound to the actual incoming request, and an actual owner-browser network test. No source-only observation in this report is a tested runtime guarantee.
