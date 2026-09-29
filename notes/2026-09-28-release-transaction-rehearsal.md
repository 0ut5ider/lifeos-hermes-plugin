# Coordinated release rehearsal

Date: 2026-09-28. Target: the separate `lifeos-install-probe` account on `.212`. Its Hermes and LifeOS roots are distinct. The account has no running gateway service.

The release transaction stages the current Hermes code, installed bridge code, Hermes config, and LifeOS system files in a private snapshot. It records hashes for the current and candidate code trees. Apply refuses a changed candidate before stopping the gateway. It copies the candidate code, runs LifeOS `OverlaySystem.ts`, checks the installed system files, then runs an executable verifier. A failure restores the staged code and LifeOS files. A manual restore command uses the same snapshot.

The first live attempt failed before the overlay because Bun was absent from the test account's default `PATH`. The transaction restored the code that it had already copied. The snapshot state became `rolled_back`; no release marker remained. Bun was found at `~/.local/bin/bun`, and the next test used that directory in `PATH`.

The second live attempt ran the actual LifeOS overlay. It reported one updated file and one created file. The verifier confirmed that candidate markers existed in Hermes, the bridge, and LifeOS, then exited 42 by design. The transaction returned failure, marked the snapshot `rolled_back`, and removed all three candidate markers. SHA-256 checks for synthetic files under `LIFEOS/USER` and `LIFEOS/MEMORY/STATE` passed.

The third live attempt used a verifier that accepted those same three markers. Apply returned `applied`. A manual restore returned `rolled_back`, removed all markers, and preserved the same two user-data hashes. Four local transaction tests and five system snapshot tests pass. The broader bridge suite had passed 302 tests with 55 optional skips before this transaction script was added.

This establishes code and system-file rollback on an account without a gateway. It does not verify a real gateway stop, restart, model route, Discord delivery, changed hook registration in `settings.json`, or new dependencies. The candidate used synthetic marker files, so it is a rehearsal, not a deployable compatibility set. The update control in the dashboard must remain unavailable until a pinned, tested set and a service-backed apply and rollback check exist.

The snapshots and candidate tree are under the test account's `~/workspace` directory. `scripts/release_transaction.py restore` can restore an applied snapshot. The latest rehearsal snapshot is `~/workspace/release-snapshot-212c`; it is already in `rolled_back` state. The test account's production data and the `.211` and `.213` hosts were not changed.
