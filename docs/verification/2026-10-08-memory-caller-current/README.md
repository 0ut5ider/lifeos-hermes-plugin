# Current native caller inventory

Date: 2026-10-08. The current scan uses the prepared finance-view candidate.

The preceding scanner finds 236 candidates in 1,579 public source files. It selects memory names but omits USER-only source names. The expanded scanner finds 330 candidates in the same tree. The 94 added paths include the enabled native morning brief. That path now has [14 focused behavioral checks](../2026-10-08-morning-brief/README.md).

The [current source identity](source-identity.json) verifies all 330 file hashes against the prepared tree. The current inventory contains 66 files with a governed API reference. The other 264 files require classification. A reference alone does not verify every branch in a file. Candidate counts do not measure complete behavior coverage.

The scanner reads public program sources. It excludes physical USER and MEMORY records, dependency trees, build output, tests, and symlink files. It traces imports, hook registrations, command declarations, and retained manual entry points. Dynamic paths still require manual review. The selected daily profile determines which optional entries remain inactive.

The historical seed, `source-traces.json`, identifies earlier candidates. The scanner replaces source lines, source hashes, and registration evidence with current values. It refuses a historical path absent from the selected tree. The [baseline](inventory-baseline.txt) demonstrates two failures: stale evidence survives, and an absent source receives an empty-text hash. The [corrected gate](inventory-final.txt) passes three checks. It also verifies discovery of a USER-only program without reading a USER record.

The [added paths](added-user-candidates.json) retain explicit unresolved classifications. The [preceding identity](preceding-source-identity.json), [initial scan](scan-output.json), and [expanded scan](expanded-scan-output.json) preserve the discovery sequence. The [current scan](current-scan-output.json) describes the finance-view candidate. Earlier seed hashes and source lines do not establish current behavior.

Complete classification, installed ownership acceptance, and combined release verification remain open.
