# Continuous installation lease

Date: 2026-10-05. This candidate unit keeps one operating-system installation lock across service draining, profile backup, ownership changes, configuration return, and service restart. Production configuration remains unchanged.

The installation lock issues an explicit lease to its owning process and thread. Profile helpers can borrow that lease without releasing the outer lock. The lease checks the physical profile and lock identities and their owner permissions. It refuses expired leases, another profile, another thread, a forked process, replaced lock files, changed permissions, and forged values. Ordinary lock calls retain exclusive acquisition. A caller must pass the lease explicitly.

The failing controls first refuse the unsupported lease argument. The combined profile control then refuses the unsupported helper argument. Both results remain in this directory. The final implementation adds optional lease arguments to the service barrier, profile backup creation, and ownership transaction. It adds no dependency and changes no upstream patch.

The combined control uses actual private systemd services with parent and child writers, a native profile backup, and the ownership configuration transaction. One lease covers drain, backup, stopped-state verification, reviewed configuration publication, configuration return, and restart. Actual competing processes cannot acquire the lock at four points in the sequence. They can acquire it after the outer operation exits. Borrowing after fork and from another thread also uses actual execution.

The final gate passes **59 tests and 50 subtests in 72.87 seconds**, with no skips, failures, or errors. It includes installation leases, existing installation locks, service recovery, profile backup and separate recovery, and ownership configuration controls. `final-command.json` records the exact command, environment, and source hashes. `final-output.txt` and `final.done` record the result. `source-comparison.json` confirms that tested sources remain unchanged and that no fixture service remains.

`native-outcomes/combined-profile-lease.json` records the synthetic backup, ownership plan and return journal, and restarted service journal. Adjacent service and ownership outcomes remain under their own directories. The gate uses actual programs and systemd effects. It does not use a live private model or the deployed application services.

The lease is an internal composition mechanism. It does not implement the combined coordinator, application health, owner-turn acceptance, detached writer draining, program recovery, or production activation. Separate profile recovery still acquires its own lock and does not borrow a lease. Those requirements remain part of the combined release.
