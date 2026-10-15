# Removal publication review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Do the previous component fixes close their measured findings, and can the joined publisher recover after removing actual native software?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `80341b04`, feature/memory-portability.

Disposition: The previous three component findings are closed at their measured boundaries. Two new findings remain in the joined publication core: one P1 recovery dependency and one P2 protected-target admission gap.

This review does not certify the pending preparer, manager removal actions, dashboard controls, standalone launch, or final installed proof. Their absence is not a finding in this core review.

## Previous findings and responses

| Previous finding | Current response | Independent result |
| --- | --- | --- |
| Additional LIFEOS tools survive while their dependencies are removed. | Inventory scans LIFEOS and explicitly excludes retained USER, MEMORY, Pulse state, and known generated files. | The extra-tool refusal control passes. |
| A new Pulse override stops the gateway before refusal. | Stop validates every current service binding before the first service stop. | The real-service override control passes without changing gateway PID. |
| Retained or staged directory edits escape the second publication boundary. | Apply and resume recheck directory inputs after retention and verify final retained identities. | Both retained-copy and staged-candidate controls pass. |

All four previous boundary probes pass in 4.346 seconds. The current publication, program transaction, inventory, service, and retained-state suite passes 34 tests in 22.577 seconds.

## New findings

### 1. P1: Removing MemorySystem.ts prevents later apply recovery and software rollback

Location: optional/lifeos_release_manager/removal_publication.py, the native transaction in apply and rollback. The dependency comes from lifeos_hook_bridge/memory_access.py, NativeMemory._transaction and NativeMemory._boundary.

The publisher enters NativeMemory._transaction before it publishes or restores software. That transaction always calls _boundary, which requires the installed LIFEOS/TOOLS/MemorySystem.ts file. Complete removal legitimately deletes that file.

The supplied publication fixture removes SyntheticRemoval.ts. It retains MemorySystem.ts, so its normal rollback and first-target interruption cases do not exercise this dependency.

The new probe copies the public native tools into a private physical fixture directory. It then includes the actual MemorySystem.ts file in the reviewed program removal plan. It does not modify the shared qualified tools source.

Measured normal sequence:

1. Apply completes and reports verification_required.
2. MemorySystem.ts is absent, as required by complete software removal.
3. A new publication instance attempts rollback.
4. Rollback stops the Hermes services.
5. The native transaction refuses with `The native LifeOS memory tools are unavailable` before software restoration.

The resulting gateway, dashboard, and Pulse PIDs are all zero. The normal software rollback path cannot restore the program whose absence causes the refusal.

A second probe interrupts apply at programs-published after the actual tool is removed. Apply recovery fails through the same missing-tool check. This second probe uses an exception checkpoint; the supplied baseline separately verifies an actual process exit after its first selected target.

Evidence: memory-tool-rollback.json, memory-tool-resume.json, review-removal-publication-boundaries.stderr, and publication_probes.py.

Required correction: The removal-only native writer barrier must remain usable after native program removal. Preserve physical data boundaries, owner admission, existing writer serialization, current schema validation, and pending-publication refusal. Do not weaken the normal memory API's tool admission or introduce a raw-record bypass. Test recovery and rollback after actual MemorySystem.ts deletion.

The primary agent responds with a dedicated removal data barrier that uses retained data validation, the existing memory transaction lock, and an existing SQLite database without migrations or native tool execution. The primary agent also extends the protected-path checks. Those working changes follow this review's captured commit and are not certified by this report.

### 2. P2: The personal-data guard admits an ancestor directory containing the native store

Location: optional/lifeos_release_manager/removal_publication.py, constructor target validation.

The constructor refuses targets at or below the protected native USER directory. It does not refuse a directory target above that protected directory. ProgramTransaction permits that target because its snapshot is elsewhere in the profile.

The probe prepares an actual directory removal entry for the fixture account's .config/LIFEOS directory. That directory contains USER and the native store. It binds the exact entry digest into the private owner plan and removal marker. RemovalPublication accepts the plan.

The probe does not apply this unsafe data target. Admission alone demonstrates that the claimed personal-data safety gate is incomplete. The future preparer should never select this path, but the core guard must reject an invalid server-owned plan rather than relying on every caller to avoid ancestors.

Evidence: personal-data-ancestor.json, review-removal-publication-boundaries.stderr, and publication_probes.py, test_native_data_ancestor_is_never_a_removal_target.

Required correction: Reject directory entries that contain protected data or recovery paths, in addition to entries within those paths. Keep the checks for fixed native data aliases, current built-in memory, SOUL.md, and retained recovery sources. Add positive controls for legitimate program directories so the guard does not block software removal.

## Retained authority and mutation boundaries

The baseline retains the exact owner policy and original profile grant boundary. It refuses another owner and a later selected program edit before stopping services. The actual retained-state tests continue to honor a live owner revocation and reject changed retained source files.

The publication core rechecks native signatures under the native writer barrier. It retains current built-in memory when software rolls back. The original rollback control verifies a later built-in memory edit survives. These controls pass.

The findings do not claim an unauthenticated request can forge a removal plan. The ancestor probe constructs a private reviewed plan through the same fixture mechanism as the core tests. It tests the final safety boundary against an invalid internal plan.

## Method and limits

The reviewer changes no product files, commits nothing, and pushes nothing. The review accesses no remote hosts, reads no personal data, and calls no memory or journal tools.

All new test data is synthetic. Native tool copies remain within the disposable fixture. Tests use actual ProgramTransaction preparation and actual user-systemd service fixtures under the existing fixture lock. They retain exact program entry digests, owner plans, and service review signatures. No filesystem, native database, or service manager is replaced with a mock.

The copied previous probes remain unchanged apart from their artifact directory. The new three probes fail intentionally for the two measured core findings. The primary agent receives exact reproductions before changes and continues preparer work in separate files.

## Source and raw evidence

source-hashes.json records nine source and test files from commit 80341b04. source/ preserves their exact bytes. Raw runner JSON receipts, stdout, stderr, and completion markers remain beside this report. publication_probes.py contains the new reproductions. previous_component_probes.py preserves the previous four boundary controls.
