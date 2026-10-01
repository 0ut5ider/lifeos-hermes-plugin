# Managed native PULSE HTTP relay

Date: 2026-10-01. Branch: `feature/lifeos-memory`. All data is synthetic. No running installation changes.

## Implemented boundary

Native PULSE delegates four exact read routes to the plugin's protected Hermes owner API. Each request uses incoming bearer or supported host session cookies. Ambient agent context and `LIFEOS_MEMORY_INTERNAL` do not authorize HTTP requests. The relay uses a fixed literal loopback destination, refuses redirects, disables ambient HTTP proxies, and bounds responses to 3 MiB. Successful responses identify the intended Hermes profile, installed LifeOS root, and principal. Denied or unavailable responses never select raw native reads.

A separate native collector supplies the plugin's governed projection after its owner and physical-source checks. It does not call the public HTTP handler. This separation fixes the authenticated 503 that the first implementation produced.

Native managed detection persists through a private `memory-http.json` marker. Connector loss remains unavailable after a process restart. The later ownership transaction must create this marker before it enables managed operation. Removing both the marker and connector deliberately returns a new process to standalone mode. These files are installation state, not credentials.

The private `pulse_http.dashboard_base_url` identifies the server-to-server loopback destination. The optional `dashboard_browser_url` identifies the user-visible dashboard address and prefix. A denied response can link to that configured sign-in address. It never supplies an internal loopback address or an upstream-provided redirect as the browser sign-in link.

## Tests and evidence

- `before.txt`: native requests return raw memory without authentication, omit cache protection, and do not enforce revocation. This initial fixture also collected the imported parent test class. Later fixtures import its module instead.
- `preparation.txt`: the first source preparation input already contained the requested branch name. The preparation failed before publication.
- `after.txt` and `after-dependencies.txt`: fixture setup failures and authenticated 503 results. The missing YAML dependency is resolved by linking the existing owned public runtime dependencies. The trusted projection then exposes the HTTP-handler recursion.
- `fixed.txt`: 35 cases pass after collection separates from HTTP admission.
- `boundary-before.txt`: invalid view types and missing private configuration reproduce unsanitized failures.
- `installation-before.txt`: a different local installation returns an accepted success before response binding.
- `incomplete-before.txt`: a truncated HTTP body returns success before declared-length validation.
- `browser-address-before.txt`: a separately configured browser address is rejected before the public address field exists.
- `focused-final.txt`: the final 61-case projection, owner authentication, preferences, relay, and transport gate passes in 46.374 seconds.
- `browser-final.txt`: the Chromium program passes again against the final implementation.
- `transport-final.txt`: 21 transport and native network cases pass in 19.361 seconds.
- `bound-relay-gate.txt`: the earlier 59-case projection, authentication, preferences, and relay gate passes. It predates the final response-length and browser-address cases.
- `browser-first.txt`: the browser child initially cannot find its installed development dependency under the synthetic HOME.
- `browser-second.txt`: actual Chromium login form, four native requests, cross-origin denial, and logout pass. The child uses the existing installed Playwright package and browser cache. No browser package is added to the plugin.
- `preparation-final.txt`: all five patch bundle and real source preparation cases pass without skips.
- `probe_browser.py`: the browser program. It does not inject tokens. The synthetic owner signs in through the pinned Hermes form.

Sources: Hermes base `758ad514eb0e800547e015edf05aa18f78b78d82`; LifeOS base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Ordered preparation uses the distributed patches. The existing LifeOS memory patch now changes 18 files. The two copies are identical. There are still nine Hermes patch groups and ten LifeOS patch groups.

## Limits and next gates

The native network fixture loads the actual distributed `modules/memory.ts` on a disposable Bun listener. It does not start all PULSE modules or validate graph and wiki interfaces. Chromium verifies the four JSON views through separate localhost ports and host cookies with the root cookie path. Secure transport, a LAN browser, a reverse-proxy prefix, and a full PULSE UI are not established by that result. Unsupported managed `/api/memory/` routes currently refuse explicitly.

The full source inventory must govern derived readers before ownership activation. Managed restore, staged publication, restricted prompt and final delivery cases, lifecycle coverage, and recoverable setup remain open. The broader memory regression follows this focused unit. That regression is not the final release gate.
