# Governed native upgrade store

Date: 2026-10-08. The release remains staged. These cases use synthetic records and actual native store APIs.

The [baseline](baseline.txt) runs eight tests and records 15 failed assertions. Unbound and revoked callers read, create, change status, and expire records. Read-only callers create, change status, and expire records. Retired records remain visible, and private creation persists record and state files. Native field and selected file-effect comparisons pass before the change.

The exported list, detail, creation, status, and expiry APIs now use the current owner service. The service admits retained records through the fixed `UPGRADES/records` boundary. It validates notes and creation input with the existing native text boundary. Creation requires owner publication and proposal-creation authority. Status changes and expiry require owner publication and approval authority. Read-only owners retain list and detail access.

The native parser, record constructor, renderer, and transition rules retain the record format. The native planner returns declared publications without changing files. The owner service rechecks source bytes and caller authority after planning and before each publication. It journals record and state files together, supplies authenticated session attribution, and creates private output files. It refuses changes to registered fact sources without explicit fact review.

The [final focused gate](final-gate.txt) passes 24 tests. It compares all 36 status-transition pairs and their complete file effects with the preceding prepared native store. It also compares list and detail fields, creation, and expiry effects. The control includes the previously accepted collision-resistant record identifier. Timestamp normalization permits only native UTC timestamps and their generated identifier prefix.

The focused gate checks unbound, revoked, read-only, and missing proposal grants. It checks private input, retired sources, redirected files, malformed arguments, authenticated attribution, source changes, destination changes, retries, and concurrent creation. Four actual process exits interrupt record or state publication. Recovery restores the original store. Revocation between record and state publication also restores the store.

The [later-edit recovery baseline](later-recovery-baseline.txt) shows that generic recovery restores an interrupted record even after a later edit. The upgrade operation now supplies exact planned output hashes to the existing transaction capability. Recovery preserves a later edit in place and refuses the ambiguous recovery. The [digest recovery gate](digest-recovery-gate.txt) passes 19 cases before the remaining five checks are added.

Malformed store state has an explicit safety difference. The original creation replaces malformed state with a new deduplication state. Managed creation preserves malformed state and refuses until explicit recovery. A characterization case records both effects. Malformed expiry dates retain the native skip behavior.

The [first gate](first-gate.txt) refuses admitted fixtures because the source allowlist lacks the upgrade records directory. The [service probe](source-admission-probe.txt) verifies that reason. The [admitted repeat](admitted-gate.txt) passes eight cases and finds one error in the new expiry comparison: it expires an invalid date. The corrected comparison passes the [nine-case gate](nine-case-gate.txt). Raw failed runs remain visible.

The [adjacent gate](adjacent-gate.txt) passes 157 tests with warnings treated as errors. It includes proposal delegation, proposal decisions, exported hypothesis helpers, authenticated hypothesis review, native HTTP, owner publication, recovery, dashboard authority, preferences, and shared events. The command and completion status remain on disk. The [dependency receipt](dependency-selection-final.json) verifies identical manifests and frozen locks before using accepted dependencies. The [source receipt](source-identity.json) records the current product and native hashes. Both patch copies have identical bytes.

This gate covers the native upgrade store APIs. It does not establish authenticated combined upgrades HTTP, installed application acceptance, complete caller coverage, or ownership activation. The candidate remains local, and `.252` retains its deployed baseline.
