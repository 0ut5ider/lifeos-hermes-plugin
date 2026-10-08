# Current authority before native publication

Date: 2026-10-08. Scope: the daily text release candidate. Ownership remains disabled on `.252`.

The [initial experiment](before.txt) revokes caller access after real native reads or validation. It finds nine failures. Some explicit writers pass because their first permission check follows publication-path planning. The [interior experiment](before-interior.txt) moves revocation into the subsequent callback validation and source reads. It finds 13 failures in 14 tests. A response check can refuse a result after the native writer already changes persistent state.

The service now forwards current caller checks to native fact creation, whole-file curation, and proposal decisions. Hot curation and archive publication recheck authority after native validation and routing. Explicit remember, correct, and forget operations also check immediately before their native write or registry mutation. These checks use the current configuration, resolved scope, and Discord audience when applicable. The existing operation journal and retry identities remain unchanged.

The [focused experiment](after.txt) passes all 14 tests. It runs actual Bun tools and SQLite transactions in isolated synthetic stores. Observers revoke configuration after a completed read or validation. Each test checks native publication actions and the resulting current files or references. An unchanged-authority control confirms that a real native fact still publishes.

The [combined writer gate](focused.txt) passes 161 tests without skips. It includes native facts, proposals, direct native delegation, explicit service calls, sharing, runtime capture, private file modes, interrupted publication recovery, proposal cleanup, and Hermes session consolidation. The [runner](run_gate.py) records its exit status in `focused.done`.

The installed profile review finds ten group-writable directories and an external plugin link. The [permission preparation](prepare_profile_permissions.py) records the original directory modes, stops and resumes the three selected services through `ProfileServices`, and sets the measured directories to 0700. All three services restart with `UMask=0077`. The [receipt](profile-permissions.json) records the operation. The [new admission check](profile-admission.json) reports no directory failures. The external plugin link and absent managed connector remain open prerequisites for the tested candidate installation.

To undo the directory changes, drain the selected services, restore the recorded directory modes, and resume them against the unchanged definitions. Then remove the three recorded `backup-privacy.conf` files and reload the service manager. Take a fresh service preview, drain, and resume to restore the previous creation mask. Do not change definitions while a stopped-service journal awaits recovery.

No candidate plugin code deploys in this unit. The installed application tests, scheduled local-owner authority, final Discord delivery check, installed backup recovery, and combined release acceptance remain open. These checks reduce the permission change window; they do not make Discord permission updates atomic with local publication.
