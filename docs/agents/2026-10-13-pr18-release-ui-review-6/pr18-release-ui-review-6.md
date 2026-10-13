Date: 2026-10-13
Role: Independent focused package consistency reviewer
Question: Does PR18 check extracted release metadata and native source manifests against the downloaded archive before imports, and keep fresh recovery in one qualified lease namespace?
Model: gpt-6.1-sol, high reasoning effort

Reviewed head: 579a23e21f72553ec6c773d4cbbaecdc5b6be3ac
Exact inspected source hashes: reviewed-file-identities.json
Scope: the revised bounded ordinary code review of release_stage.py, release_plan.py, their recovery source selection, and existing stage/operation controls.

## Result

This focused review is clear. I found no remaining concrete defect in the corrected archive/manifest consistency checks, bounded regular-owner reads, or fresh recovery lease namespace.

All 30 requested existing controls pass. This closes the round 5 extracted-manifest trust defect for the reviewed boundary. It does not establish successful browser installation, current guest recovery, conversational update, or complete release qualification.

## Before-import consistency

The archive path is fixed under the operation's download directory. Its filename uses the certificate's validated version and program commit prefix. archived_manifest requires a valid SHA-256 digest, a positive bounded archive size, a regular owner file, and exact byte count and digest agreement with the certificate. It opens the archive without following a symlink and without blocking on a substituted FIFO.

The reader streams the archive and requires exactly one regular DAILY-CANDIDATE.json member. The member is bounded to 512 KiB. It also limits archive members and total declared extracted bytes. Missing, duplicate, oversized, or linked manifest members refuse before source import.

validate_package reads the extracted manifest through the bounded owner-file helper. It then compares the exact extracted bytes with the manifest bytes from the authenticated archive. A coordinated extracted program edit plus matching local file-map edit can no longer become the expected source map. The expected bytes come from the downloaded archive, not the mutable extracted manifest or a newly calculated request value.

The authenticated main manifest must contain exactly the two expected native source-manifest paths. Their hashes must be valid SHA-256 values, and their actual bytes must match those hashes. This check occurs before bridge imports. Recomputing a native tree digest in a changed native manifest cannot replace that externally bound expectation.

The bridge, release-manager, and Python closure file maps are also validated before load_bridge. The native validators subsequently verify supported base commits, patch identities, and native tree contents. The ordering addresses the previously confirmed problem in which candidate import ran after a coordinated local map edit.

## Bounded file reads and errors

read_manifest refuses aliases, nonregular files, another owner's file, empty files, and files larger than 512 KiB before parsing. It also limits the read itself to 512 KiB plus one byte. It uses O_NOFOLLOW and O_NONBLOCK, so manifest symlinks and FIFOs cannot act as ordinary metadata inputs.

The archive reader performs its regular-file and owner checks before hashing or parsing. Malformed certificate identities, unavailable archives, invalid archive members, unequal extracted bytes, and unequal native manifest hashes return ReleaseRejected. These branches do not select active programs or create a compatibility path for unsupported artifacts.

The reads remain metadata and source checks. This review accesses no personal memory records and issues no owner authorization or memory policy substitute.

## Fresh source and lease identity

release_plan determines freshness before it chooses the current bridge. A fresh operation selects the candidate directly. It no longer imports a changed installed bridge and only afterward overwrites the selected result.

For a sealed plan marked fresh, recovery_bridge validates the plan and package, then returns the candidate source. The fresh controller receives the same execution current module that issues its installation lease. Existing nonfresh operations retain their active or retained bridge behavior and three-service controller.

The actual sealed-archive regression extracts the unchanged 8e package and creates a canonical archive hardlink in the disposable operation download directory. It copies an installed bridge separately, obtains a real filesystem installation lock, and borrows that lease through the fresh service controller. It also puts a RuntimeError sentinel in the copied installed bridge. Fresh inspection selects the candidate without executing that sentinel and preserves the absent native destination.

The namespace correction does not substitute owner authority. Fresh recovery still refuses newly enabled managed ownership through the existing administration.required check. Request/action admission and the recorded plan checks remain present. This focused review adds no compatibility execution or data reset.

## Controls run

The final command runs test_release_stage and test_release_operation with the exact supplied sealed build and historical prepared operation fixtures. It passes 30 tests in 46.332 seconds: 13 stage controls and 17 operation controls. There are no skips, failures, or errors. The command uses -B and treats ResourceWarning as an error.

The stage controls execute real synthetic import markers. They verify the exact-map acceptance and refusal before that import marker for coordinated extracted map changes, changed/missing/symlink/FIFO archives, symlink/oversized/FIFO extracted manifests, altered native source manifests, and missing/duplicate/oversized/linked archive manifest members. These are component controls with synthetic filesystem inputs, not browser or end-to-end installation evidence.

The operation controls include the real sealed-archive lease and installed-source sentinel case. They also retain the existing plan, admission, worker-lifetime, locking, and failure-publication controls.

Unittest writes its normal verbose report to final-python.stderr. final-python.stdout is empty. No ResourceWarning or unexpected diagnostic occurs. The initial 28-control working-tree run also passed, but the final 30-control result is the current reviewed gate.

The exact arguments and selected environment fields are saved in command.json. That file contains no credentials or unrestricted environment export.

## Scope limits

The primary revised the task to an ordinary review and existing tests only. I followed that instruction and developed no additional native coordinated-edit or retained-worker execution experiments. The earlier round 5 raw proof remains unchanged.

This clear result covers package metadata binding, source-manifest consistency, bounded reads, and fresh lease identity. It does not claim that retained job worker bytes are revalidated at every later launch. That earlier question was outside the revised review scope.

Successful current guest review, installation, interruption recovery, subsequent user update, and final sealed release qualification remain separate evidence gates. I did not mutate a guest, alter configuration or external services, edit product source, commit, push, or call memory/journal tools.

## Raw data

- reviewed-file-identities.json: exact committed head and inspected hashes.
- final-reviewed.diff: committed archive binding, bounded-read, native hash, fresh source selection, and regression changes.
- initial-working-tree.diff: first working-tree snapshot before the later bounds/native-map corrections.
- command.json: exact final test arguments, selected environment, outcome, and elapsed time.
- final-python.stdout/final-python.stderr: final 30-control output.
- python.stdout/python.stderr: preserved initial 28-control output.
