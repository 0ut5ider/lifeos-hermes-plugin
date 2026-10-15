Date: 2026-10-15
Role: Independent focused code reviewer, delegated by the primary Cerebo agent
Question: Does excluding the exact profile-root portability runtime prevent recursive backup traversal while preserving owner files, inspection integrity, and explicit recovery limits?
Model: gpt-6.1-sol, high reasoning effort

## Disposition

CLEAR for the captured one-entry runtime exclusion correction and its component interactions. I found no actionable defect. The independent profile backup and recovery run passes 49 tests with clean diagnostics. Four additional real filesystem and recovery controls pass.

This report does not qualify the installed cycle, any older archive, or a full guest backup. The current installed `10ac` archive lacks this correction and cannot qualify it. The previous source-selection `f8e0d25b` and environment `10ac` clear results retain their respective limits.

## Measured problem and selected boundary

The primary reports that an installed activation preparation reaches 99,945 entries plus 56 pending entries and exceeds the unchanged 100,000-source limit. Of those, 99,177 entries and 48 pending entries are retained removal runtimes under the exact `.hermes/.lifeos-portability` root. I did not access the guest or read those contents. The primary cancelled that incomplete preparation through the owner recovery control before ownership apply.

The local regression places an oversized sparse artifact under `.lifeos-portability/<job>/removal/stock-runtime`. Before the correction, backup attempts to inspect that runtime artifact and refuses. The preserved primary red result demonstrates unintended traversal, not an independent replay of the installed 100,000-entry count.

The correction adds only `'.lifeos-portability': 'runtime'` to `EXCLUDED_TOP_LEVEL`. Existing traversal evaluates the exclusion before descending or reading the entry. `_exclusion()` consults this mapping only when the relative path contains exactly one component. It does not exclude similarly named paths or nested owner directories. Source count and byte limits remain unchanged for all included data.

## Independent verification

Command:

```text
python3 docs/verification/2026-10-15-memory-portability/run_tests.py review-portability-runtime-backup-current test_profile_backup test_profile_backup_recovery docs.agents.2026-10-15-portability-runtime-backup-review.backup_probes
```

Result: 49 tests pass in 58.771 seconds. Runner duration is 59.002 seconds. Process and runner exit codes are zero; `unhandled_diagnostics` is false. I inspected the complete output. The run uses real synthetic native records, SQLite databases, files, subprocess barriers, backup creation, archive inspection, and separate recovery. It does not mock a complete installed cycle. No real service-manager mutations were needed.

The existing suites cover coherent profile and native snapshots, real concurrent writers, write-ahead-log histories, interruption, private staging, configuration and native reference retention, internal links, unreviewed external-link refusal, recovered histories, captured tools, and separate disabled recovery candidates.

The supplied new regression verifies the exact runtime exclusion and leaves its oversized source artifact intact. It also proves that similarly named root notes and nested `workspace/.lifeos-portability` owner bytes are included.

The four independent controls provide these measurements:

| Control | Result |
|---|---|
| Back up an exact runtime plus three neighboring owner paths, change the live runtime after backup, inspect, then recover separately | The runtime exclusion appears in backup and recovery receipts. No omitted runtime copy is claimed. Three owner files recover byte for byte. Later live runtime state and the live native fact remain intact. Candidate ownership and sharing remain disabled. |
| Use an exact root `.lifeos-portability` symlink to a synthetic external runtime containing a FIFO | Backup records the exclusion without following the symlink. Source link and target bytes remain unchanged. No runtime link copy is claimed. |
| Use an external link at `.lifeos-portability-notes` or `workspace/.lifeos-portability` | Both paths still refuse backup before publication. The synthetic external owner bytes remain intact. |
| Alter the exclusion reason or add a copied directory beneath the excluded root | Inspection refuses invalid reasons and overlapping included/excluded metadata. Restoring the original reviewed manifest passes inspection. |

These controls are in `backup_probes.py`; safe outcome receipts are `recovery-exclusion.json` and `root-symlink-exclusion.json`.

## Inspection, recovery, and provenance limits

The archive lists `.lifeos-portability` once as a runtime exclusion. It contains no file, directory, or link copy for that excluded root. Inspection still checks the reviewed manifest signature, source lists, file hashes, native signature, parent coverage, and included/excluded overlap. The exact root's permitted reason is `runtime`; changing it to another supported reason does not pass.

Separate profile recovery restores only included profile and native data. It carries the exact exclusion list into `.profile-recovery.json` and leaves ownership and sharing disabled. The independent recovery control verifies that omitted runtime state is not presented as restored and does not overwrite the live runtime.

The exclusion is selected by its reserved root name. It does not authenticate the provenance of arbitrary contents placed there. The safe claim is that this data-only backup omits that root and declares the omission, not that it verifies or copies every job or rollback runtime. This matches the existing treatment of `.lifeos-releases`. Full guest backup is the separate mechanism for retaining release workspaces and rollback artifacts. This correction does not delete those live artifacts; it does not independently prove a new full guest backup or restore.

## Preserved primary results

`primary-cycle-backup-runtime-red` contains the expected oversized runtime read refusal. The focused green result is preserved separately.

The initial extended run named `cycle-backup-runtime-green` is a FAIL because it asks for nonexistent `test_profile_recovery`. Its passing actual tests do not make that run clean. The corrected run uses `test_profile_backup_recovery`. Completed primary receipts are retained with `primary-` prefixes. They remain supplied evidence, separate from the independently executed clean 49-test run.

## Exact captured source

SHA-256:

| File | SHA-256 |
|---|---|
| `lifeos_hook_bridge/profile_backup.py` | `44a90010aefcfb66ddbbeb9cd0a079d1846d42b241205089add89759b60aed20` |
| `lifeos_hook_bridge/profile_backup_recovery.py` | `52d410e948f2457dd83395cd8a376cef817dfa7e1c2e116ccdb2fefdf94c58f0` |
| `lifeos_hook_bridge/memory_ownership.py` | `3b0edfd1c33140563d9ef8908626c2e17d12a84cf8063c222e6f3c2987b33ae1` |
| `lifeos_hook_bridge/ownership_setup.py` | `6881e17fbce66919458a61ca64c6008e4fadda215fc3bbd3943048e17720486e` |
| `tests/test_profile_backup.py` | `3d07606f33662b9b632b5f86c51db3d91ee2aa399d470bb28468cb6b6af711a3` |
| `tests/test_profile_backup_recovery.py` | `666f4051bf8461e0e8b086f17c75f3a94a5023425ba4f0120c2f2fb162b0b371` |

Exact source bytes are in `source/`. `source-stability.json` verifies that all captured files remained unchanged at report time. `backup_probes.sha256` pins the independent controls. Runner JSON, stdout, stderr, and done markers are retained in this directory.

## Remaining acceptance

The corrected package still needs the actual installed activation cycle that previously stopped at backup admission. Full installed removal, retained recovery, reboot, model-turn, and release qualification claims remain separate. No product code, remote systems, personal records, memory stores, journal stores, or Git state were changed by this review.
