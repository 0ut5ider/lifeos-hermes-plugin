# Authenticated managed installation mounting

Date: 2026-10-02. Role: Cerebo, primary implementation and verification.

## Implemented boundary

A managed native mount needs explicit installation owner authority. A conversation identity cannot authorize installation. The dashboard uses the actual Hermes session and checks its current owner binding. The plugin issues a signed private grant for the fixed LifeOS installation and Hermes profile.

The grant permits only prompt bundle, preview, and publication operations. It does not permit arbitrary recall, fact writes, source approval, or publication into another profile. Source validation and retirement checks remain required. Installation does not switch memory ownership.

The grant binds the current configuration, owner account, purpose, and expiration. A detached update also binds the job path, request digest, and action. A changed queued request requires fresh authorization. Recovery creates a fresh grant for the recovery action. An apply grant cannot authorize recovery.

Finalization uses a ten-minute grant. Detached update and recovery use a one-hour grant. The plugin stores the signing key and grants under the private profile directory `.lifeos-memory-admin`. It checks owner permissions and refuses symlink grant files. The grant pathname is a bearer credential. Public status responses do not include it.

Native subprocesses receive the grant without conversation metadata or an internal bypass flag. Each native prompt request checks current authorization again. Publication checks authority after rendering and before the atomic prompt write. Normal completion and handled failure revoke the grant. A process death leaves a grant that expires; recovery requires another authenticated request.

## Installation and update integration

`Finish LifeOS setup` uses the grant for the actual native mount and mount check. Hermes configuration validation and VersionDrift baseline creation remain required. A handled failure restores the existing mount snapshot. A managed configuration or connector without valid owner authorization refuses before mounting.

The detached update worker checks the grant before systemd operations and uses it for mounting and verification. A tampered job cannot consume another valid grant. Accepted work revokes the grant when it finishes or raises an exception. An expired grant refuses before an update starts. A recovery request issues fresh action-bound authority.

If recovery cannot launch, the API revokes the new grant and restores the prior request and status. This preserves a retryable job. The update queue removes a new job and revokes its grant if launch fails.

The implementation adds plugin-owned Python code. It adds no dependency and changes no Hermes or LifeOS patch group. The standalone installer uses the same module through its existing file-based loading convention.

## Verification

The focused gate passes 55 tests in 22.024 seconds with no skips, failures, errors, or warnings. [focused-after.txt](focused-after.txt) records the result. Native cases run Bun mounting, the pinned Hermes configuration checker, and actual VersionDrift baseline creation. The authenticated finalization case uses real Hermes password login and FastAPI routing with a synthetic candidate at its exact fixture revision.

Update queue and recovery cases use real authentication, private files, signatures, and request validation. They replace only systemd launch and service queries. These are component tests. They do not establish live service stop, swap, restart, or recovery acceptance.

Tests cover forged, expired, revoked, incorrectly encoded, and incorrectly permissioned grants. They cover changed configuration, connector loss, job and action substitution, another profile, missing owner accounts, anonymous requests, fabricated owner headers, and revoked dashboard bindings. A controlled interleaving revokes the grant after actual native rendering and verifies that publication preserves the prior prompt.

The initial missing implementation is recorded in [before.txt](before.txt). [initial-failure.txt](initial-failure.txt) records fixture and sanitized-refusal corrections. [native-install.txt](native-install.txt) records an incorrect test exception assertion. [dashboard-before.txt](dashboard-before.txt) reproduces the recovery launch failure. [legacy-fixture-failure.txt](legacy-fixture-failure.txt) records an incomplete FastAPI substitute; the fixture now uses the real framework. [gate-selection-failure.txt](gate-selection-failure.txt) records an incorrect test-module name. The corrected selections retain all required assertions.

[run_gate.sh](run_gate.sh) runs the bounded neighboring gate. Its final result is recorded after completion.

## Limits

This grant is an administrative application boundary. It does not protect against a hostile process with the same operating-system identity. That process can access the private signing key and profile files. The existing source and memory transaction boundaries assume cooperating local processes.

Managed detection checks the connector and profile configuration. Removing both is not a supported ownership transition. Persistent ownership setup and removal markers remain part of the recoverable ownership transaction.

Prompt publication is atomic. Complete crash recovery across all mount files is not added here. A failure after an atomic write can have an unknown outcome; finalization restores its snapshot on handled failure. Native update recovery retains its existing transaction semantics. Memory schema 4 rollback compatibility remains a separate acceptance requirement.

PULSE remount authority, automatic trusted-release source classification, source-review page controls, alternate and derived readers, restricted delivery, retained-session reconstruction, recoverable ownership activation, and independent release review remain open. No browser click, live systemd update, or full release gate is claimed. No server configuration changes or deployments occur in this batch. Memory ownership stays disabled on running installations.
