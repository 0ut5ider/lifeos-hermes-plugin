# Managed proposal cleanup

Date: 2026-10-08. Scope: native `ProposalGC` in the daily release candidate. This result does not activate ownership or complete the native writer inventory.

The native cleanup reads and replaces four identity and preference files directly. The [baseline](before.txt) confirms four failures: missing context, revoked ownership, restricted write permissions, and public file permissions. Two characterization controls retain native duplicate selection and the unattended removal ceiling.

The candidate delegates managed cleanup to the memory service. The service admits the current sources, invokes the native parser, rechecks sources and caller permissions, and publishes through the existing recovery journal. The service confines publication to four native targets and the cleanup log. It rejects symbolic links, hard links, retired content, and invalid source data. It publishes private files and preserves the native frontmatter stamping behavior.

The native command retains dry-run, routing, apply, and bounded unattended modes. The unattended command retains its fail-silent exit behavior. A refused managed request writes no cleanup output. The standalone controls retain native behavior without a connector.

Twelve [recovery controls](recovery.txt) pass. Additional controls cover retired content, hard links, and unattended refusal. Real subprocess controls revoke ownership after native rendering, change a source before publication, and terminate after the first actual write. Recovery restores previous bytes and permits a fresh cleanup.

The broader gate finds a callback regression in `MemoryService.call_context`. The proposal writer supplies its SQLite connection to the permission callback. The callback accepts only zero arguments and raises `TypeError`. The candidate accepts the optional connection argument and retains its authority check. Existing proposal and explicit fact controls verify the correction.

The [final gate](focused-final.txt) passes 102 tests and 102 subtests without skips. It includes proposal cleanup, native proposals, explicit fact creation, Discord audience checks, native TELOS and timestamp writers, patch consistency, and source preparation. The earlier [failed gate](focused.txt) retains the callback failure.

No live runtime or ownership configuration changes occur in this unit. The native change is bundled in both copies of `lifeos-memory-access.patch`. Installed memory activation, session harvesting, scheduled-job authority, final Discord delivery permissions, backup recovery, and combined release verification remain open.
