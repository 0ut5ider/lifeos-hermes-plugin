# Final portability and removal review

Date: 2026-10-15

Role: Independent read-only safety reviewer.

Question: Does the final local removal assembly preserve exact return and native-source binding, later built-in memory, owner authority, executable selection, and recoverable publication?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed baseline: `3ff669f7`, on `feature/memory-portability`. Reviewed generated-output correction: `4db55b096a8fe5248803dfce963483e9befa111d`. The intervening fixture cleanup at `5a073032` and strict runner are included in clean verification. The reviewed current contract is captured with its own hash.

Disposition: CLEAR for the final local code and component review after the generated-output correction. No new measured actionable defect remains in this review. The generated-output P2 reported by the primary agent closes locally. Forty Python controls and 19 SDK controls pass cleanly.

This is not a release certificate. Complete installed removal, authenticated retained-helper recovery after removal, reboot, and real model-turn acceptance remain separate installed gates. The task brief reports installed progress, but the reviewer neither accesses that guest nor treats those reports as independent local proof.

## Generated-output P2 and closure

The primary agent reports that normal native documentation hooks regenerate `LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md`. The previous initial removal target loop compares that file to shipped source. Its later unknown-file scan already treats the exact path as generated. Those inconsistent classifications can refuse ordinary removal before a plan is produced.

The correction derives the exact existing `GENERATED_FILES` set before target selection and omits those paths from deletion targets and their before-image map. It does not exempt the documentation directory or an arbitrary filename pattern. The existing set contains the architecture summary path.

The independent current inventory controls verify:

1. The regenerated summary remains outside removal targets and before-image metadata.
2. Actual ProgramTransaction application retains its current bytes.
3. Actual restoration retains those bytes again.
4. A symbolic link at the generated path still refuses.
5. An adjacent unreviewed owner document still refuses and remains intact.

These controls pass under correction `4db55b09`. The P2 is closed locally. Installed replay of that correction remains a primary-agent acceptance task.

## New independent recovery controls

`recovery_probes.py` adds three controls using actual synthetic native data, actual user services, real program publication, and actual child processes.

### Exit after rollback drain

The probe applies removal, writes a later built-in fact, and starts rollback in a fresh child. The child exits with status 74 after the service drain checkpoint. The parent writes another later built-in fact and resumes rollback.

Rollback restores software and the returned owner policy, keeps Pulse stopped, and restarts the reviewed Hermes services. Both later memory edits remain intact. Repeating rollback returns the same terminal state without replaying historical memory.

### Exit after program restoration

The second probe exits with status 74 after the actual program restore completes but before service restart and the terminal rollback state. A later built-in edit follows that exit.

Recovery accepts the existing restored program state, resumes service recovery, and reaches `rolled_back`. A repeated rollback remains idempotent. The later memory bytes remain intact.

The real child sources use the retained bridge and fixed synthetic service bindings. Their exact retained file map and plan signature are updated only inside the disposable fixture. These are failure-injection controls, not mocked program transactions.

### Built-in edit after fresh constructor proof

The third probe removes the selected fixture software and runs the actual fresh stock Hermes constructor. After that real proof returns, the probe changes the built-in memory file before final verification completes.

Verification refuses the stale proof and retains the later bytes. The operation stays `verification_required`. A second actual constructor verifies the current bytes and reaches `verified`. No model turn runs in either constructor probe.

Safe receipts: `rollback-drained.json`, `rollback-programs-restored.json`, and `late-builtin-verification.json`.

## Assembly and authority assessment

Preparation requires the exact verified return workflow, its operation identifier and signatures, returned ownership, and the unchanged native export. The current native signature check prevents a new fact from being silently omitted. Later built-in memory remains outside software publication targets.

The program plan carries explicit before-image identities for transformed configuration, native settings, qualified programs, and launchers. Per-entry publication and restoration checks refuse later target or retained-copy edits. Protected-path checks exclude both descendants and ancestors of personal data and recovery sources.

The removal data barrier retains the shared writer lock and exact existing schema-4 database boundary without requiring the removed native tool. It refuses pending publication, physical database changes, and writes. It performs no migration or content recovery.

Removal selects an exact reviewed stock source and executable identity. Covered-link and executable-cache boundaries remain those cleared in the prior reviews. The command helper fixes the contained cache prefix, and selected commands disable bytecode writes. The final constructor proves current built-in selection and absence of active LifeOS providers and plugins.

Retained recovery validates private marker and plan binding, exact bridge and manager source maps, and the retained returned-owner policy. It preserves the original profile grant boundary. A current live policy continues to override retained owner authority. Standalone authentication uses the current private dashboard password configuration and actual native password provider.

Manager actions require the current owner and exact reviewed request and signature. A live removal marker excludes other workflow and release actions. Preparation remains separate from software application. Rollback restores software into the returned configuration, rather than reactivating historical native ownership.

No new measured owner-binding, cross-job, native-data, or retained-source defect is established.

## Earlier objections and preserved clearances

The review does not re-report corrected findings:

- The early service journal, cancellation, source-reference, and manager recovery findings remain closed under their primitive and workflow closure reports.
- The removal data barrier closes the deleted native-tool recovery failure and protected-ancestor admission failure.
- Explicit before-image admission closes the transformation-to-transaction lost update.
- Exact runtime identity closes later launcher, interpreter, dependency, and executable-cache changes.
- Covered target checks close contained links into unbound or explicitly excluded runtime regions.
- The coordinator exemption remains limited to the exact workflow unit, current MainPID, cgroup, fragment, and trusted non-consuming drop-ins.

The prior coordinator review at `bb7d3007` remains CLEAR with 21 controls, including the four reviewer boundary probes that the primary agent independently repeats. The covered-link review at `13c0ac38` remains CLEAR. The runtime and coordinator implementation does not change in the reviewed generated-output correction, so those complete suites and command-startup probes are not repeated here.

## Browser and user controls

Nineteen current SDK controls pass with empty stderr. They cover import and export review, explicit decisions, owner refusal, stale-poll ordering, separate application, local account and model-route disclosure, and explicit Discord-disable acknowledgement for removal.

The actual local HTTP controls in the Python suite reject unauthenticated sessions, another owner, forged action fields, client-selected paths, and foreign origins. They retain owner status access after active memory configuration removal.

SDK controls are component fixtures. Local HTTP controls use actual native sessions. Neither establishes a complete installed browser workflow, a remote Discord interaction, or a model turn.

## Warning handling and clean evidence

The first wider run completes 34 assertions but emits an ignored SQLite ResourceWarning from an existing test fixture. The primary agent independently identifies the same leak. This report does not count that run as clean qualification. Its receipt and raw output are retained as `initial-recovery-unclean.*`.

The fixture correction closes the SQLite connection explicitly. The revised runner also fails a run that contains ignored exceptions or ResourceWarning diagnostics, even if the Python process returns zero.

The clean repeat, `review-final-removal-clean`, passes 40 tests in 54.826 test seconds, with runner wall time 55.489 seconds. Its receipt records:

```json
{
  "exit_code": 0,
  "process_exit_code": 0,
  "unhandled_diagnostics": false
}
```

The repeat includes the three new recovery controls, publication, data barrier, retained authentication and state, manager workflow, exact preparation and generation, actual local HTTP, and current native inventory. There are no failures or skips.

`ui-current.stdout`, `ui-current.stderr`, and `ui-command.json` preserve the 19 passing SDK controls. Runner stdout, stderr, JSON, and completion markers remain beside this report.

## Source provenance and limits

`source-hashes.json` records 33 baseline source and test hashes, the current contract hash, four correction and test-runner hashes, and the reviewer probe hash. `source/` and `corrected-source/` retain those exact bytes. The only reviewed removal product difference from the baseline is the explicit generated-output correction.

The initial test process starts while the primary agent prepares that inventory correction. It does not run inventory tests. The clean repeat uses the committed correction and corrected fixture. The retained manager copies in synthetic publication tests can include the current inventory source, but those publication controls do not call native inventory. The independent clean inventory controls are the closure evidence for that function.

The reviewer changes no product files, makes no commits, stages nothing, and pushes nothing. No remote hosts, personal source records, memory tools, or journal tools are accessed. All data and changed services are synthetic fixtures. Actual user-service mutations use the existing fixture lock and clean up owned units. No daily or development deployment changes occur through this review.
