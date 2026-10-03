# PULSE request identity and host integration

Date: 2026-10-01.

The owner API reuses real Hermes dashboard authentication. It resolves the verified provider and account against the current private memory configuration. The account lookup and owner scope use one configuration snapshot. The API does not infer authority from arrival on localhost or an agent environment variable.

The first review passes 35 cases but finds two error-path defects. A corrupt native registry escapes as an HTTP 500. Host authentication and framework denials bypass endpoint cache headers. Synthetic regressions reproduce both. The API catches database errors and returns sanitized HTTP 503. Pure ASGI middleware covers the exact memory route prefix, including host-generated denials.

The real host imports plugin routers during app assembly, before startup. The plugin uses the already-loaded app at that point. It does not import or start Hermes itself. A disposable profile and actual public dashboard source confirm installation. HTTP 401, 200, 422, and 405 responses all have no-store. This keeps the change inside the plugin rather than adding a Hermes patch.

The corrected primary gate passes 38 cases in 19.432 seconds. Real localhost HTTP verifies forgetting and owner-binding removal between requests. Forty concurrent ASGI requests verify prefix isolation and unchanged unrelated headers. The actual host startup emits a SQLite version warning and selects its non-WAL mode. The evidence retains that warning; no unrelated dependency change is made.

The tested Basic provider has stateless bearer tokens. Browser logout removes cookies, but a copied valid bearer still works until expiry. Removing the memory account binding denies that bearer on the next request. Authentication delegation must preserve this limit rather than promise host-session revocation that the provider does not implement.
