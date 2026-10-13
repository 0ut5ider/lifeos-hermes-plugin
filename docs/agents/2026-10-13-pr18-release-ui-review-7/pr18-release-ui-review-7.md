Date: 2026-10-13
Role: Independent focused retained-worker launch reviewer
Question: Does PR18 validate the retained worker against the qualified package before admission and preserve owner-grant cleanup on refusal?
Model: gpt-6.1-sol, high reasoning effort

Reviewed head: e5a6ccf132dbed65adfc5305f9a080dfcb28dd2d
Comparison base: 579a23e21f72553ec6c773d4cbbaecdc5b6be3ac
Exact inspected source hashes: reviewed-file-identities.json

## Result

This bounded follow-up is clear. I found no concrete defect in the two launch validation lines, their ordering, the refusal regression, or the existing API owner-authorization cleanup path.

All 38 selected existing CLI, stage, and operation controls pass. This establishes the component refusal boundary. Actual final guest installation, recovery, update acceptance, and complete sealed release qualification remain separate gates.

## Qualified worker consistency

launch_worker obtains the fixed operation request and validates job/package against its certificate. The package validator authenticates the downloaded archive, compares the extracted main manifest's exact bytes, checks both native source manifests, and validates the qualified source file maps.

The next line compares every job/worker file with manager_files from that authenticated manifest. It requires the exact file map and forbids unrecorded bytecode. A changed, missing, additional, escaping, or linked retained worker artifact cannot serve as the reviewed executable copy.

Both checks occur before admit_operation. Admission therefore does not publish a queued action or transfer the owner grant into the operation request when the retained worker differs. Both detached execution branches occur afterward, so the same validation protects systemd-run and the direct subprocess path. The ordering is independent of apply, recover, or restore.

The change validates an existing copy against qualified bytes. It does not replace a changed worker, accept a newer local map, or add a fallback source. A later edit causes refusal. The README describes exactly this pre-admission guarantee.

## Regression and test interpretation

The new CLI regression creates an actual private operation and an authenticated synthetic package fixture. It copies the manager files into worker, changes one retained file, and calls the real launch entry point for all three actions.

Each action receives ReleaseRejected before admission. The operation's ready state remains unchanged. No admission.json or worker-launch.json appears. The fixture uses minimal metadata intentionally: if execution reaches admission, its missing fields do not conceal that ordering error. The actual file-map check fails first.

This is a filesystem and control-flow component test. It does not assert that a complete installation succeeds. It does not fake an end-to-end owner approval or guest update.

## Owner authorization cleanup

The authenticated API can issue a native mount grant before it calls commands.launch. apply_release keeps that path in its local authorization variable until launch returns successfully. A package or retained-worker validation exception occurs before admit_operation and before request publication. The API catches the refusal and returns HTTP 409. Its finally block still revokes any locally issued authorization.

After a successful launch, apply_release sets authorization=None because the admitted worker now owns that cleanup obligation. The existing worker failure and bounded grant cleanup controls remain unchanged and pass in the selected operation run.

This cleanup ordering is assessed from source. I did not add or run a new authenticated dashboard grant-issue-plus-retained-worker-refusal experiment. The existing operation tests use synthetic grant files to verify recorded worker cleanup and path bounds. They are not evidence of a live personal-memory grant.

The correction does not change current owner checks, grant binding, native memory policy, personal data, model selection, or service admission. A normal command-line action without an owner grant remains subject to the existing native mount refusal.

## Controls run

The exact command runs test_release_manager_cli, test_release_stage, and test_release_operation with the supplied sealed 8e build and historical fresh operation fixtures. All 38 controls pass in 90.524 seconds: eight CLI controls, 13 stage controls, and 17 operation controls. There are no skips, errors, or failures.

The command uses -B and treats ResourceWarning as an error. Unittest's normal verbose result appears in python.stderr. python.stdout is empty. There are no unexpected warnings or diagnostics.

The stage controls retain coordinated manifest/source refusal, canonical archive authentication, bounded manifest reads, native source-manifest binding, and exact source-map validation. The operation controls retain the real sealed-archive fresh lease and installed-source sentinel case, action admission, process lifetime, failure publication, and recorded grant cleanup.

I performed no additional experiments or guest operations. The primary's earlier synthetic-guest changed-worker observation is context supplied in the review brief. I did not claim to rerun that observation.

## Scope limits

This clear result covers the committed two-line retained-worker launch correction and its selected neighboring controls. It does not establish successful current guest HTTP review, first installation, interruption recovery, subsequent user update, or final release qualification.

The reviewed guarantee is validation immediately before admission and launch. This report does not claim immutable execution against arbitrary concurrent same-account filesystem modification.

I edited no product source, changed no configuration or external service, mutated no guest, committed no change, pushed no branch, and called no memory or journal tools.

## Raw data

- followup.diff: exact 579a-to-e5a6 source, README, and regression diff.
- reviewed-file-identities.json: exact inspected head and source hashes.
- command.json: exact arguments, selected environment, outcome, and elapsed time.
- python.stdout/python.stderr: full 38-control output.
