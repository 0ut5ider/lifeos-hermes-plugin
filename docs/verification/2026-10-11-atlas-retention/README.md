# Governed Atlas history retention

Date: 2026-10-11. Adrian authorizes development item 2 after merging PR8.

The existing `hermes lifeos-job atlas-sync` path archives history automatically. It uses the admitted current graph and selected Gear and Projects sources. This development change adds no new schedule, source collector, model request, dependency, or native patch. The daily `.253` plugin remains the certified 0.2.0 release until a tested release update.

## Retention and provenance

The default policy activates above 64 retained runs or 128 lifecycle events. It targets a recent window of 32 runs and 64 lifecycle events. It additionally preserves every source and edge observation run reference, each collector's newest run identifier, and each collector's maximum completion timestamp. Asset identifiers, observation freshness, and native sweep behavior remain intact.

The planner copies admitted database bytes into private in-memory SQLite state. It trims that copy before asking the actual native collector planner to reconcile current sources. No live file changes during planning. If the planned graph exceeds capacity, the planner tries a 16-run, 50-event window and then a window containing only protected runs. It never discards a protected run or current inventory to force a pass. An intrinsically oversized inventory or already unadmitted graph remains refused.

Before trimming reaches publication, the operation archives the exact prior database and snapshot bytes. Its manifest binds their SHA-256 values, the expected new graph and snapshot, source digests, current scope, retirement state, removal counts, and creation time. The archive identifier is the SHA-256 of that manifest without its identifier field. Current reads verify the complete manifest bytes and both preserved files.

The public snapshot adds archived counts to retained collector run and success counts. Retention does not reset those totals. Structural insight metrics continue to come from the actual current native graph. The sync result reports the archive identifier, removed counts, selected window, and actual capacity. The recent lifecycle window can shrink under capacity pressure. Exact older events remain in the archive.

## Publication and recovery

Archive files use mode 0600 in private owner directories. Fixed digest paths refuse aliases, hard links, shared permissions, and existing archive files. The three archive files publish before the live database and snapshot. All five files share the existing owner transaction journal. Current owner authority is checked between writes. Final verification checks every output before committing the receipt.

An interrupted process restores every prior group member. A later archive or live graph edit blocks the complete recovery group. The journal remains available for review. Recovery can leave empty private archive directories; it does not remove unrelated directories.

Whole-guest backup coverage must include the complete external Atlas directory, including archives and pending governance journals. Native and profile-only backups still omit that external directory. The grouped filesystem restore test exercises archive preservation and current owner reads after restoration. It does not claim a new Proxmox Backup Server restore or a daily-server release deployment.

## Current owner archive access

Use the identifier returned by an archiving sync:

```sh
hermes lifeos-atlas-history ARCHIVE_ID --table sync_run --offset 0
hermes lifeos-atlas-history ARCHIVE_ID --table lifecycle_event --offset 0
```

The command reads at most 100 rows per page. Follow `next_offset` until it is null. It admits the selected local owner and model route without requesting inference. Read-only, disabled, revoked, malformed, and unrelated destinations fail admission. A current retirement policy can withhold old text without altering the private archive files. Archives do not enter automatic memory recall. This release retains archives and has no automatic archive deletion policy.

## Evidence

The [initial behavioral regression](before.json) demonstrates absent archive behavior. The [capacity-pressure regression](pressure-before.json) fails at 10,006 fields against the 10,000-field cap. The [provenance regression](provenance-before.json) demonstrates the incomplete manifest check. The [timestamp regression](timestamps-before.json) demonstrates a changed maximum collector timestamp. The [command regression](command-before.json) demonstrates the missing Hermes command. Each failure remains recorded with raw output.

The initial packaged-source harness lacks the installed `yaml` dependency. That setup failure remains under `harness-missing-yaml`. The corrected local harness uses the retained complete prepared native source with installed dependencies. The subsequent `after` and `after-empty-snapshot-fix` records retain development iterations. `private-directories`, `focused`, and `combined` are chronological intermediate gates. Final receipts identify their exact source hashes and verification scope.

The first remote harness also requires the installed native dependencies and the guest Python interpreter. Its [setup report](development-harness-development-verification.json) remains recorded. The next [remote report](development-environment-before-development-verification.json) passes the retention cases but fails three inference cases because the staging script removes the launcher's executable permissions. A [direct Bun probe](development-launcher-diagnostic.json) reports `EACCES`. The final staging operator preserves executable source files as mode 0700, other files as mode 0600, and verifies both source hashes and modes before and after the suite.

The final [local gate](release-gate.json) passes all 106 tests in 370.932 seconds, with unchanged source hashes and no skipped tests. The [raw test output](release-gate.stderr) includes the complete result. This selected gate covers Atlas retention, capacity, synchronization, owner access, insights, jobs, grouped recovery, command registration, and plugin lifecycle.

The final [.252 development gate](development-verification.json) passes the same 106 tests in 349.362 seconds, with no skipped tests. The [raw guest output](development.stderr) includes the complete result. All 672 staged source hashes and modes match the current branch and remain unchanged during verification. The live profile configuration hashes remain unchanged. Hermes gateway, Hermes dashboard, and Pulse remain active, each with zero service restarts.

The [independent review](../../agents/2026-10-11-atlas-retention-review/atlas-retention-review.md) finds no confirmed blocker or implementation defect in `c9fdf51c..72b0d4a2`. The reviewer repeats 22 focused cases and checks two additional native cases. The [primary verification](../../agents/2026-10-11-atlas-retention-review/primary/verification.json) independently repeats all 24 cases, with unchanged source hashes and no skipped tests. The additional cases preserve all 252 assets and required run references at the zero-window fallback, with 9,978 graph fields. They also preserve mixed success and partial-run totals across two archives and an older maximum completion timestamp. No implementation change follows the review.

The review records nine trailing-whitespace lines in a historical raw stderr receipt. The implementation, tests, and authored documentation pass the whitespace check. The retained receipt remains exact.

The [local runner](run_checks.py) records actual native reconciliation, private local HTTP and SDK fixtures, subprocess termination, and exact filesystem publication. The [development operator](verify_development.py) stages the complete plugin and tests in isolated `.252` profiles. It checks the live configuration and service state before and after verification. These checks send no Discord messages and use no daily personal data.

Outside Git, the operator creates isolated directories under `/home/lifeos-hermes/development`: `2026-10-11-atlas-retention`, `2026-10-11-atlas-retention-final`, and `2026-10-11-atlas-retention-verified`. These directories contain staged source and test receipts. Removing those directories after retaining the receipts reverses the staging work. The live plugin selection and the daily `.253` installation do not change.

The [publication audit](publication-checks.json) checks source compilation, JSON records, documentation links, and credential exclusion. The current branch remains local. A pull request review and a tested release package remain required before daily deployment. This selected gate does not repeat the full daily release suite or perform a new off-server guest restore.
