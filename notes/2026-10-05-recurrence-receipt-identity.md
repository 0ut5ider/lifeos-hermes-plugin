# Recurrence registry retry identity

2026-10-05, staged LifeOS plugin. The first governed registry candidate included the previous destination digest in its operation payload. A second request with the same identifier and same patch record then conflicted with its own receipt. The first write changed the registry digest, so the service interpreted the retry as a different operation.

One actual service regression reproduces the conflict in 0.53 seconds. The operation now identifies the request by its stable record and installed base. The service still checks current policy before receipt lookup. A new publication checks previous destination bytes before and after native rendering. The expanded gate passes 69 tests and 35 subtests, including exact receipt reuse without another append and later destination edit preservation.

The destination digest is a publication precondition, not part of the stable request identity for an append operation. This finding concerns the native recurrence registry. It does not establish idempotency for every publisher.
