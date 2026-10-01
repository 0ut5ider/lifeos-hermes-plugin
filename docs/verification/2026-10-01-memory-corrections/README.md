# Fresh memory review corrections

The fresh review identifies four defects at implementation interfaces. These corrections preserve the approved memory ownership design. The work uses owned public source and synthetic profiles. It makes no live configuration change.

## Dashboard owner authorization

Every private memory dashboard route requires a verified Hermes Session. The preferences operations check its qualified account against the same configuration that supplies the installed root and owner scope. Sharing, enrollment, and revocation check the owner binding again inside the configuration update. Internal owner helpers retain their existing trusted use without an HTTP identity. Private responses, including host denials, disable caching.

Four regression cases fail before the correction. They cover disabled host authentication, revoked bindings, distinct authenticated accounts without a binding, and a revoked forget operation. The corrected 34-case dashboard, preferences, and sharing gate passes. A separate three-action race case passes after removal of the owner binding between initial authorization and configuration update.

`dashboard-after.log` preserves the intermediate failed run. Two failures come from a fixture override that needs the added account argument. The third comes from the host's shared password-login rate limit. The corrected fixtures preserve real authentication and use the host's test-only reset to isolate rate-limit state between tests. `dashboard-final.log` and `dashboard-owner-race.log` contain the passing results.

The correction adds no Hermes or LifeOS patch. Memory ownership remains disabled. The broader native coverage, relay, lifecycle, installation, and release requirements remain open.

## Reference authorization before recovery reads

Publication path selection uses the mutation scope. A fact reference must have the required write grant, active status, and current revision before the journal receives its source path. Proposal decisions require their approval grant and current pending revision. A denied or stale callback can still record its refusal receipt, but its empty publication set opens no source file.

Two regressions use actual Python file-open audit events. Before the correction, eight category, project, and stale-reference subcases open forbidden or obsolete sources. After the correction, all refuse without source access or byte changes. The complete native, proposal, and authorization gate passes 40 tests in 25.041 seconds, including publication interruption, retry, and recovery controls. The files `source-authorization-before.log` and `source-authorization-after.log` retain both results.

## Explicit hot-memory publication

Explicit hot remember requires read and write grants for the current file. It verifies the whole native snapshot before duplicate detection or publication. It uses the existing verified curation operation, with the explicit writer's source metadata. Adoption remains a separate reviewed action. Project-note publication retains its native archive path.

The before run fails six subcases across unadopted principal and assistant entries, outside additions, changed recorded entries, and a missing read grant. The corrected native, curation, adoption, and authorization gate passes 48 tests in 49.989 seconds. The controls verify byte preservation on refusal, existing references, explicit provenance, duplicate and retry behavior, and a usable governed read after adoption. Evidence is `hot-publication-before.log` and `hot-publication-after.log`.
