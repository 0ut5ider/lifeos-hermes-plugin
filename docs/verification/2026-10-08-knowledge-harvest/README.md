# Governed native Knowledge harvesting

Date: 2026-10-08. This candidate uses Hermes `758ad514eb0e800547e015edf05aa18f78b78d82` and LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.

The [initial five command checks](before.txt) find three unauthorized writes and one missing governed receipt. The standalone control passes. Native source mining bypasses the managed memory service for unbound, revoked, and read-only callers.

Managed harvesting now delegates to the existing owner service. The service admits fixed WORK, RESEARCH, rating, queue, state, and registered current Knowledge sources. It validates source text and source labels against native validation and retirement history. Existing Claude project memories remain outside the fresh managed store. Source files and directories must stay within their physical owner paths. The source count limit is 2,048. Each source has a 256 KiB limit. The source corpus has a 3 MiB limit. Native batches retain the limit of 50 candidates.

A scoped synchronous native file interface runs the original scanners, classifiers, duplicate selection, staging format, backlink analysis, and expiry algorithm. The interface has no physical-file fallback. It retains the observed directory order. The service checks authority and source identity after rendering and before publication. Staging, queue deletion, harvest state, archive moves, and the master index use the existing recovery journal. Generated files have mode `0600`.

Managed expiry preserves each original note at `_archive/<Domain>/<filename>`. It refuses occupied archive destinations. It retires the matching registry facts and preserves their retained claim history. People and Companies keep their principal access requirement after archival. Unregistered notes remain preserved and excluded. Standalone LifeOS retains its flat archive and ordinary command behavior.

The [final prepared-source gate](combined-final.txt) passes **180 tests**, with warnings treated as errors. The gate includes:

- 27 focused harvesting checks, including an actual process exit during staging and after expiry deletion.
- Exact native note, queue, state, and output comparisons for queue limits, WORK parsing, and RESEARCH parsing.
- Correction and forget controls, current authority, source changes, link refusals, archive collisions, private entity access, and backup integrity after expiry.
- Neighboring staged decisions, canonical reads, native facts, backups, delegation, session consolidation, proposal cleanup, and policy checks.
- Patch, native installation-source, and capability validation checks.

The [retained receipt baseline](retry-before.txt) shows that an old successful request can expose a later-forgotten source label. The service now checks retained receipt output before it returns a retry. An unchanged retry still returns the original receipt.

The [source preparation result](prepare.txt) applies all eleven Hermes groups and twenty-three LifeOS patches. The root and runtime memory patches are identical. The [historical evidence check](ledger-final.txt) passes after preserving the earlier plugin manifest at its original hash. This preservation does not change the historical acceptance claims.

The [first implementation output](first.txt) retains a 40-second retry deadlock. The receipt check held one memory transaction while starting another. The receipt check now runs outside the source collection transaction. The identified orphaned connector was stopped. Later intermediate outputs retain test-fixture ordering and backup-manifest assertion errors. The [directory probe](directory-order.json) compares actual Python and Bun listings. The native comparison now verifies identical candidate order after fixture restoration.

Native review, status, contradictions, and index command authority remain a separate open unit. Installed gateway, dashboard, and Pulse acceptance remain open. This gate does not enable ownership or deploy the daily server.
