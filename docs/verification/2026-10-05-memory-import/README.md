# Hermes memory import primitive

Date: 2026-10-05. This candidate implements review and selected native publication. Production ownership stays disabled. Adrian selects names Adrian and Cerebo for a fresh `.212` store with no existing-data import.

The final regression passes **149 tests** without skips, failures, or errors. [The command](regression-command.json) records the exact modules, prepared source paths, and changed-code hashes. [The output](regression-output.txt) and [exit marker](regression.done) retain the result. The suite uses real native LifeOS tools, actual Hermes password sessions, real files, and child processes. Existing neighboring tests also contain component fixtures; this result does not claim complete browser or service acceptance.

The 18 import tests cover complete byte accounting, byte order marks, newline normalization, blank and duplicate occurrences, immutable private snapshots, native duplicates and retirement, unsafe text, changed sources and permissions, reviewed destinations, capacity, native persistence, provenance, retries, and interrupted commits. Authenticated HTTP checks cover preview and snapshot creation, origins, profile overrides, and revoked owners. Three publication-mode tests verify Python and actual Bun journal metadata, exact mode recovery, and invalid-mode refusal.

[Boundary controls](boundary-before.txt) reproduce inconsistent review metadata and a source change after the last native commit. [Corrected controls](boundary-after.txt) pass both tests. Failed publication leaves an explicit conflict or partial result. Native receipts stay available for recovery. Setup never changes ownership as part of import.

[The private-source proof](source-parsing-proof.json) compares authorized copies of the two `.213` built-in source files with the pinned Hermes parser. Both source copies preserve their original bytes. Five synthetic parsing controls also match. Native fact and operation counts remain zero. [The verifier](verify-hermes-source.py) reads a private tar archive outside Git. Source bodies, private snapshots, and the archive are excluded from this evidence. `.211` record access remains blocked by the shared-memory connector integrity error.

The first broader run uses an incomplete hook-test tree. [Its retained output](trimmed-source-regression-output.txt) reports five failures and two errors because the native PULSE proposal library is absent. This run does not pass. The corrected command selects the complete prepared source tree and passes. [The earlier complete-source run](pre-boundary-regression-output.txt) passes 147 tests before the two boundary regressions are added.

The importer currently supports principal, assistant, and project fact destinations. Learning publication, reviewed splits, effective runtime provider verification, writer draining through ownership cutover, authenticated plan/application controls, operation status, browser acceptance, reverse migration, return conflicts, and removal remain open. Semantic conflict detection remains incomplete. Known retirement checks and exact duplicate checks are enforced.

Recovery captures original regular file modes with new journals. Historical journals that lack modes cannot establish their original permissions. This unit adds no Hermes or LifeOS patch group and does not deploy a release.
