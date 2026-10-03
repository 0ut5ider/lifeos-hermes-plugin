# Governed PULSE memory views

## Scope

The plugin projects four native memory views: snapshot, state, health, and runs. Tests use real Bun readers and synthetic private homes. The public source fixture is `source-gate-20261001-cortex-final`. No running installation changes.

The projection checks owner source authority before native file reads. It checks physical input paths, current registered hot entries, and missing active sources. Retained text receives correction and forget filtering. The native cadence, counts, windows, and route shapes remain available.

Current hot entries come from registry-verified native files. The projection renders their count and JavaScript UTF-16 character count. Historical filtering and current-entry publication use the same memory transaction. A cooperating forget cannot pass between these operations.

Dynamic object field names receive retired-claim checks. Declared operational names remain at their exact schema locations. Field names use current retirement matching. Historical values also use their report timestamp. Encoded object keys receive the retained-content checks.

## Preserved failures

The real native HTTP baseline returns private synthetic markers without request credentials. This happens with missing context, ambient owner context, and a broken connector. The probe uses the real memory route handler in an isolated localhost server. It does not start the complete PULSE listener or use real account data.

The initial independent snapshot review finds two defects despite 66 passing tests. A valid corrected fact disappears when its text contains the superseded claim. Retired claims survive in dynamic JSON field names. The primary reproduces both. The unchanged probes pass after correction.

The first closure finds incorrect field-schema inheritance and missing fixed fields. The primary 70-case gate also fails two health clock cases. The next 71-case gate exposes a remaining historical field-name error. All original failures remain in this directory. The correction separates report-value age from current field-name retirement matching.

## Commands

Run from the repository root:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python \
  -m unittest test_memory_pulse test_memory_cortex_health test_memory_diagnostics -v
```

The baseline, failures, and corrected results have distinct files. Independent reports and raw probes are in `docs/agents/2026-10-01-memory-pulse-snapshot-review/`.

The final primary gate passes 72 cases in 44.507 seconds. The final independent gate passes 72 cases in 45.155 seconds. Seven archived native probes pass independently and on primary rerun. The final review identifies no remaining material issue in this bounded projection. Its report is `evidence-closure/memory-pulse-snapshot-evidence-closure.md` under the review directory. Two primary commands first use incorrect probe filenames. Those command failures remain as separate files; corrected commands pass.

## Open boundaries

The projection alone does not authenticate an HTTP caller. The protected Hermes API now requires a verified dashboard session. The managed native relay and browser credential path remain open. The four routes do not include graph, wiki, context generation, or the complete PULSE listener. Ownership activation remains disabled.

## Authenticated Hermes API

The API exposes only GET requests under `/api/plugins/lifeos-hook-bridge/memory/pulse/`. Supported views are snapshot, state, health, and runs. The host authenticates the session. The plugin reloads private configuration and requires `dashboard:<provider>:<user_id>` to map to the installation principal in the existing account map. The plugin refuses service-token-only requests and disabled authentication without a verified session. Query parameters cannot supply an account, scope, or source path.

Each successful request uses current source and retirement state. Removing the owner binding blocks the next request on the same connection. Configuration faults, redirected sources, and registry corruption produce a sanitized unavailable response. The plugin never adds a new session or bearer issuer.

Plugin-owned ASGI middleware sets `Cache-Control: no-store` on this exact route prefix. It covers host authentication and framework errors. It removes ETag and Last-Modified from protected responses. Unrelated routes keep their original headers. Hermes imports the plugin while assembling its app, so the plugin can install this middleware before startup. No additional Hermes patch is required.

The primary 38-case gate passes in 19.432 seconds. Real localhost uvicorn and HTTPX requests verify all four views, forgetting, owner-binding removal, and browser logout. The real owned Hermes dashboard assembly also verifies middleware installation and protected 401, 200, 422, and 405 responses. That source emits an expected SQLite version warning and selects its non-WAL database mode. The complete warning is preserved. No interpreter, dependency, or live server change occurs.

Basic authentication uses stateless signed tokens in the tested host. Logout clears browser cookies. A previously copied bearer can remain valid until expiry. Removing its account binding immediately blocks memory access. These tests do not claim server-side bearer revocation.

The initial API review finds missing cache headers and an uncaught registry error. Both regressions fail before correction and pass after correction. Review reports are in `docs/agents/2026-10-01-memory-pulse-auth-review/`. The original failures remain in this directory.

Final independent API closure passes 38 cases in 20.273 seconds and identifies no new material finding. The primary reruns its error, binding, header, and real HTTP probes. Forty concurrent header controls preserve exact-prefix isolation, configured root paths, unrelated response headers, and idempotent installation. This closes the protected Hermes API unit, not the native PULSE relay or browser integration.
