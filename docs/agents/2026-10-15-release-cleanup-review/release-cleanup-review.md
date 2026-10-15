Date: 2026-10-15
Role: Independent release cleanup reviewer
Question: Does the cleanup operator require completed daily restore evidence and remove only the exact owned rehearsal guests and empty owned storage?
Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the corrected cleanup_release_guests.py and its controls. Both measured guard findings below are closed. No unresolved actionable finding remains in this scope.

This is a pre-execution source and local control review. It does not claim that the actual complete daily restore has passed, that the protected archive is currently verified by this reviewer, or that the cleanup has run. The operator must obtain its real evidence and current native metadata before it can proceed.

I ran no remote commands, deleted no guests or real storage, used no memory or journal tools, read no credentials or personal records, and made no source or Git changes. The local operator boundary controls record commands and outputs in memory. They do not fabricate a real guest completion receipt.

## Brief and reviewed source

The primary requested review before eventual cleanup execution. The operator must wait for the actual complete daily 0.5.0 restore PASS, process.done 0, successful removal of restored CT110, and verified backup pruning protection. It may delete only CT111, CT112, and CT113 with the exact inspected hostnames, disposable tags, and owned root volume IDs. It must preserve other guest status and remove only empty owned directory storage.

Exact current source copies and hashes are in source/ and reviewed-source-sha256.json. The original source read showed the two guard gaps. The first filesystem snapshot raced the primary correction and already includes both fixes. It is named cleanup_release_guests.initial-filesystem-snapshot.after-fixes.py and is not presented as a frozen pre-fix file.

For historical behavior controls, cleanup_release_guests.historical-guard-shape.py restores only the two guard shapes observed in the first source read while retaining the corrected operation ledger. Its first comments explain that provenance. The historical outputs characterize those observed guards, not an invented frozen full version. A local probe setup error after the ledger gained with_suffix is retained in cleanup-probe-setup-error.stderr. The probe was corrected before current closure.

## P2 finding: Storage validation occurred after destruction

The initial operator validated the storage registration type, exact path, and physical directory only after it destroyed all three guests. The guest root volume IDs still referred to lifeos-050-tests. If that storage registration was redirected, those exact IDs could resolve through the redirected registration before the later assertion refused it.

The historical guard-shape controls demonstrate the ordering. Redirected storage, wrong storage type, and a symlinked storage root each reached all three recorded pct destroy calls before refusal. No actual Proxmox operation ran.

The primary added storage_root and calls it before any shutdown or destroy. It requires the exact dir registration, /var/lib/vz/lifeos-050-tests path, exact storage identifier, and physical non-symlink root. It revalidates that registration and root before removing storage.

Current closure: all three invalid storage cases refuse before any recorded destruction. The valid synthetic case deletes exactly the three authorized IDs and removes only the owned empty directory storage.

## P2 finding: Restore-removal evidence did not bind the command

The initial evidence gate matched only a successful destroy-disposable label. It did not check the actual command. A successful row with command pct status 110 therefore passed as removal evidence when CT110 was absent from inventory.

The primary now requires exactly one labeled removal row, a strict integer exit code 0, and the exact command pct destroy 110 --purge 1. The current native inventory must independently confirm CT110 is absent.

Current closure refuses a wrong command, missing row, duplicate row, nonzero exit code, and Boolean exit code before any destructive call. It also refuses CT110 still being present. The actual completed restore and its command ledger remain required at real execution.

## Independent control results

All current controls pass:

- The primary guest validator suite passes one positive and six refusals. It checks the selected ID, exact hostname, tag, root volume, mount points, and unused volumes.
- Twenty-one independent full main-control-flow cases pass with in-memory native command boundaries.
- One actual nested run-helper control verifies that a measured nonzero exit is recorded in the operation ledger before the original CalledProcessError propagates.

The full-flow cases cover the valid path; redirected, wrong-type, and symlinked storage; wrong restore-removal command; missing backup pruning protection; failed restore status; wrong source or restored guest; wrong release version, commit, or archive digest; process.done 1; missing, duplicate, failed, or Boolean removal evidence; a wrong backup archive prefix; CT110 still present; a missing owned guest; and changed owned guest configuration.

In the valid boundary case, the command list contains exactly pct destroy 111, pct destroy 112, and pct destroy 113. The preserved inventory includes daily CT102 and processing VM801 with their unchanged type, name, and status. In every refusal case, the recorded destruction list is empty. These results are local guard tests, not end-to-end Proxmox acceptance.

The historical control output has four intended failures that characterize the fixed guards. It is not counted as a current passing suite. Raw output and stderr remain beside check_cleanup_boundaries.py.

## Other reviewed boundaries

The corrected operator verifies the actual evidence status, exact 0.5.0 identity, source CT102, restored CT110, complete process result, exact removal command, archive path prefix, and native protected flag before entering cleanup.

It checks that all three owned IDs are current LXC guests. It validates all three configurations before any mutation. Each configuration must match the exact hostname, disposable;lifeos-test tags, and lifeos-050-tests:<ID>/vm-<ID>-disk-0.raw,size=120G root volume. Any native mpN or unusedN entry refuses cleanup. After shutdown, it requires stopped state and rechecks the configuration before each destroy.

After deletion, the operator requires all three IDs absent and requires the entire remaining type/name/status map to equal the preserved map. It then rechecks the owned storage registration, requires the native content list to be empty, refuses files and symlinks in the directory tree, removes the storage registration, and uses rmdir only for the remaining empty directories. It does not recursively unlink files or touch PBS archives.

The operation ledger is written before check_returncode so an ordinary native command refusal remains recorded during partial cleanup. A PASS report is written only after all guest, preservation, storage, and empty-directory checks finish. A failure is not automatically rolled back, because deleted disposable guests cannot be restored by this cleanup operator. The primary must inspect native state and the safe ledger before deciding any subsequent action.

## Remaining execution limits

The actual cleanup remains gated on the real final restore. This review does not replace native metadata with test fixtures, approve a different storage path, or authorize additional guests. Current metadata can change between operations on a shared host. The operator rechecks the named boundaries and refuses measured differences; it does not provide a cluster-wide concurrency lock.

There is no measured finding that blocks the authorized cleanup after the real restore gate passes. The primary should retain the actual cleanup result and command ledger, then verify the final inventory and protected archive in the final evidence review.
