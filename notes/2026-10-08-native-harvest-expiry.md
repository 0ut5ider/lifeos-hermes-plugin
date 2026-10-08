# Native harvesting and retained expiry

2026-10-08, LifeOS plugin candidate on the local workstation.

Five actual Bun command checks expose managed source mining outside the governed memory service. Three refusal checks fail because the native command stages a queue candidate for unbound, revoked, and read-only callers. The receipt check fails because the command reports native text rather than a governed result. Standalone mining passes.

The candidate uses the native synchronous scanners, classifiers, staging format, duplicate selection, and expiry algorithm against declared sources. A scoped file interface collects publication intentions. It has no host-file fallback. The Python service admits fresh-store sources, checks current authority, and publishes through the existing recovery journal. Native standalone execution retains its physical filesystem behavior.

Native expiry moves every stale note to `_archive/<filename>`. Two domains can produce the same filename. Managed expiry retains `_archive/<Domain>/<filename>`, rejects occupied destinations, preserves original note bytes, and retires the registry entries. People and Companies retain their principal access requirement in their archive paths. Unregistered notes remain excluded from managed mining and expiry.

The first implementation holds a memory transaction while checking an existing request receipt, then starts another transaction. The real retry exceeds its 40-second subprocess deadline. A process inspection confirms the orphaned connector. Move the receipt check outside the collection transaction; the same five checks then pass in 1.174 seconds. The failed output stays in the verification directory. Stop the identified orphaned test connector.

The expanded comparison finds a source-order defect. The first declared reader sorts file paths. With a cap of two notes, it selects queue candidates 0 and 1. The pinned original command selects the first-created manual candidate and candidate 0. Bun returns filesystem directory order on this fixture. Preserve the snapshot directory order in the declared reader and retain the original candidate selection algorithm. Duplicate new titles still select the last candidate body.

This work does not establish installed application acceptance or activate ownership.
