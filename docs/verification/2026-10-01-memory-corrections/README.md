# Fresh memory review corrections

The fresh review identifies four defects at implementation interfaces. These corrections preserve the approved memory ownership design. The work uses owned public source and synthetic profiles. It makes no live configuration change.

## Dashboard owner authorization

Every private memory dashboard route requires a verified Hermes Session. The preferences operations check its qualified account against the same configuration that supplies the installed root and owner scope. Sharing, enrollment, and revocation check the owner binding again inside the configuration update. Internal owner helpers retain their existing trusted use without an HTTP identity. Private responses, including host denials, disable caching.

Four regression cases fail before the correction. They cover disabled host authentication, revoked bindings, distinct authenticated accounts without a binding, and a revoked forget operation. The corrected 34-case dashboard, preferences, and sharing gate passes. A separate three-action race case passes after removal of the owner binding between initial authorization and configuration update.

`dashboard-after.log` preserves the intermediate failed run. Two failures come from a fixture override that needs the added account argument. The third comes from the host's shared password-login rate limit. The corrected fixtures preserve real authentication and use the host's test-only reset to isolate rate-limit state between tests. `dashboard-final.log` and `dashboard-owner-race.log` contain the passing results.

The correction adds no Hermes or LifeOS patch. Memory ownership remains disabled. The broader native coverage, relay, lifecycle, installation, and release requirements remain open.
