# Coherent native data backup

Date: 2026-10-04. The fixtures use synthetic data and actual LifeOS tools, Hermes command discovery, SQLite, filesystem copies, and process termination. No model response or live server action is part of this gate.

The [capability check](missing-capability.txt) fails because the backup module is absent. The [initial gate](initial-gate.txt) passes seven cases and fails one inaccurate test assertion about native ranking. The corrected assertion checks retired content and the referenced status. The [registered-body probe](reference-before.txt) and [hot-entry probe](hot-before.txt) each fail before their consistency check. [Command discovery](command-before.txt) initially refuses the unregistered command.

The candidate creates a private snapshot outside the live native program and data trees. It captures the native data and serialized governance database under one cooperating writer lock. It verifies active references, complete hot entries, source stability, every copy digest, database integrity, and the installed schema. Inspection requires the bound installation and principal. The Hermes command takes its configuration from the selected profile and holds installation and configuration locks before the native lock.

The final [gate](gate.txt) passes 47 tests and 14 subtests in 133.61 seconds without skips, failures, errors, or warnings. The [command and source hashes](command.json) identify the test environment and product files. The [completion marker](gate.done) records exit status 0. Current and forgotten references survive reconstruction into a disposable native store. Actual command checks preserve built-in Hermes files and send no HTTP request. Process death before publication preserves the live store and a private verifiable stage.

Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`. LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. The fixtures apply the existing distributed patch set. This component adds no dependency or patch group.

Snapshots retain binary sources, empty directories, and original permissions and timestamps in the manifest. Backup copies use mode 0600 and directories use 0700. Collection refuses files above 64 MiB, data above 256 MiB, or more than 100,000 entries. Unsupported source redirects refuse the complete operation. Existing snapshots remain unchanged.

This component captures native USER_DATA only. It does not implement product restore, aggregate profile backup, service recovery, automatic staging recovery, or backup retention. Snapshot reconstruction belongs to the test fixture. Ownership activation remains disabled. No `.212` deployment occurs.
