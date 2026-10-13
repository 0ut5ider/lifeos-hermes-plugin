Date: 2026-10-13
Role: Independent focused fresh-recovery safety reviewer
Question: Does the fresh recovery namespace correction preserve lock admission, memory governance, and changed-package refusal?
Model: gpt-6.1-sol, high reasoning effort

Reviewed committed correction: a2655907cf3df1bfe9469b575a09ba7fa9fad67c
Comparison base: 8e020023b4d761b94495504109cc951a09ab98ab
Also reviewed: working-tree fresh-first source selection in release_plan.py.
Exact source identities: reviewed-file-identities.json

## Result

The namespace correction is sound, and its requested operation controls pass. The review is not clear for qualification because the changed-package probe confirms an additional integrity defect. A coordinated edit of an extracted source file and its local file map can pass validation and execute before an external package identity check rejects it.

The working-tree correction also closes an installed-source import gap in the initial namespace fix. The final fresh-first probe confirms that fresh recovery does not import a changed installed bridge before selecting the package source.

## P1: Extracted package file maps are not bound to the authenticated archive before imports

Location: optional/lifeos_release_manager/release_stage.py:72-95; optional/lifeos_release_manager/release_worker.py:111-117; optional/lifeos_release_manager/release_plan.py:19-26.

validate_package reads the plugin and manager file maps from extracted DAILY-CANDIDATE.json. It validates source files against that map and compares version, commit, native base, and patch counts with the certificate. The operation request binds the original archive digest, but it does not bind the extracted manifest digest. A source file and its local map can change together while the archive digest and declared version/commit remain unchanged.

The new fresh recovery selection calls this validator and then imports the package source. inspect_operation separately checks the unchanged archive digest, which does not prove that its extracted copy still matches that archive.

Measured proof: manifest_tamper_probe.py extracts the unchanged sealed 8e archive into an isolated temporary directory. It appends a harmless temporary marker write to install_source.py and updates only that file's hash in extracted DAILY-CANDIDATE.json. It calls the real validate_package against the build's fixed version, program commit, native bases, and patch counts in explicitly synthetic test certificate metadata.

Result:

- package_refused: false
- candidate_import_marker_exists: true
- original_archive_sha256_unchanged: true

The probe starts no service, performs no installation, and reads no personal records. The actual original archive remains unchanged. Its marker proves candidate code execution after the coordinated edit.

Impact: later extracted-package changes can execute before program snapshot checks reject publication. The worker can no longer claim that only the authenticated package source runs. A later refusal does not undo an import side effect.

Required correction: bind the extracted manifest to trusted prepared metadata or the authenticated archive before any candidate import. Preserve that binding through preparation, review, admission, execution, recovery, and fixture validation. A source edit plus matching local file-map edit must refuse before the import marker runs. Do not derive the expected manifest digest from the same mutable manifest during recovery.

This weakness existed in package validation before the namespace correction. The new correction relies on that validation as its fresh recovery trust boundary, so it blocks the present qualification claim.

## Fresh installed-source import gap, corrected in the working tree

The committed inspect_operation initially loads the active installed bridge and its version_drift module before computing its fresh branch. Assigning result.current=candidate afterward does not prevent that earlier import. A changed installed source can therefore execute before snapshot validation.

The primary now computes freshness first and selects candidate directly for fresh operations. Existing nonfresh source selection remains unchanged.

The final active_import_probe.py uses the unchanged sealed archive, a separate copied installed bridge, and a harmless RuntimeError sentinel in the copied installed install_source.py. It performs the real inspect_operation with fresh_recovery=True. The final result reports changed_active_source_executed=false, selected_current_is_candidate=true, and native_destination_exists=false.

An initial probe had an incorrectly permissive mode on its synthetic plan file. The validator refused that private file after the active-source correction had already prevented the sentinel. That raw failure is retained in initial-active-import-probe.stderr. The corrected private-file probe passes with empty stderr.

## Namespace and lock admission

recovery_bridge validates the operation plan and qualified package before selecting the candidate namespace for a plan marked fresh. inspect_operation now selects that same candidate namespace for fresh operations. The fresh controller receives execution current, which is the namespace that issues the installation lease.

The requested new regression extracts the real sealed current archive, places a copied installed bridge in the profile, and exercises an actual flock-backed installation lease. The service controller borrows that lease successfully. This checks the concrete cross-namespace class mismatch without mocking the lock.

The sealed plan digest prevents an incidental fresh flag edit from selecting a different branch. Request equality and action admission remain checked under the operation and installation locks. Existing nonfresh update and recovery paths retain active or retained bridge selection and their three-service controller. Their source selection was not replaced with the candidate path.

## Memory governance

The fresh namespace switch does not substitute owner authority. Fresh recovery still checks administration.required against the actual selected installation and profile. A present connector, enabled ownership, unavailable ownership configuration, or an absent installed root with owner configuration fails closed. Fresh recovery then refuses before service or native mutation and requires governed installation repair.

Native mount authorization still binds the selected profile, root, request digest, and action. Candidate namespace selection does not remove those checks. The inspection and execution paths still reject existing personal destinations without the recorded native initialization, and the native initializer preserves later user data rather than resetting it.

No memory store or personal record was accessed in this review. This assessment reads the governing source and uses synthetic package fixtures.

## Controls run

All 17 test_release_operation controls pass in 47.500 seconds with both the actual sealed build and historical fresh operation fixture enabled. The run uses -B and ResourceWarning as an error. There are no skips or failures. This includes the actual sealed-archive lease namespace regression.

The final active-source probe passes. The manifest tamper probe exits successfully because it reports the confirmed validation failure rather than asserting that the defect is corrected. Both final probe stderr files are empty. The detailed results and repeatable scripts are retained.

These controls do not establish successful current guest installation, recovery, update, or release qualification. Those acceptance gates remain separate.

## Raw data

- followup.diff: committed 8e-to-a265 namespace correction and regression.
- fresh-first-selection.diff: reviewed installed-source import correction.
- reviewed-file-identities.json: exact inspected source hashes.
- python.stdout/python.stderr: requested 17-control operation run.
- active_import_probe.py and active_import_probe.json: corrected temporary fresh-source selection probe.
- active_import_probe.stderr: empty corrected diagnostics.
- initial-active-import-probe.stderr: preserved private synthetic plan-mode failure.
- manifest_tamper_probe.py and manifest_tamper_probe.json: confirmed coordinated extracted source/map edit and import marker result.
- manifest_tamper_probe.stderr: empty diagnostics.

I edited no product source, mutated no guest, published no release, committed no changes, pushed no branch, and called no memory tools. All modified source copies belong to disposable local synthetic probe directories.
