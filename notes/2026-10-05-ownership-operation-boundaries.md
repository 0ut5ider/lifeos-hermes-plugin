# Ownership operation boundaries

Date: 2026-10-05. Role: Cerebo, primary implementation. Question: can a reviewed ownership coordinator recover across repeated setup and return operations? Model: gpt-6.1-sol.

The first combined gate passes 16 tests and six subtests. It runs actual systemd parent and child writers, native backups, and ownership configuration publication. A later gate adds process exits during backup, setup commit, service restart, and return.

The repeated-operation control finds a failure. The first setup completes and returns. The second setup then exits after draining services but before replacing the ownership transaction journal. Recovery sees the first operation's completed return journal and refuses its different signature. The gate reports one failure, nine passes, and 23 subtests in 45.90 seconds.

The journal alone cannot identify whether the new operation publishes configuration. Recovery must verify that the current configuration still matches the new reviewed backup before accepting a different completed return journal. An unfinished or committed journal with a different signature must still refuse. Native data must remain current throughout recovery.

The raw control is `docs/verification/2026-10-05-ownership-setup/expanded-output.txt`. A separate control checks an external service restart between the two configuration writes. Service draining at the beginning of an operation cannot establish that writers remain stopped for each later publication.

The external restart control also fails. The final stopped-state check refuses the active gateway, but native ownership has already become enabled. The configuration transaction must run the actual stopped-writer check immediately before each publication, including return. The initial failing result remains in `writer-before-output.txt`.

The corrected gate passes 11 tests and 23 subtests in 50.45 seconds. The final adjacent gate passes 73 tests and 73 subtests in 144.19 seconds. A fresh Hermes process verifies native provider selection and one actual model request to the scripted local endpoint after coordinated restart. Both original memory files remain unchanged and return to built-in recall after configuration return. Deployed application services and private model reasoning are separate acceptance requirements.
