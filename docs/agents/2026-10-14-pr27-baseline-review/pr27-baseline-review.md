# PR27 native baseline review

Date: 2026-10-14

Role: Independent correctness and safety reviewer

Question: Does PR27 prove an omitted native program from the exact accepted archive, preserve later edits and ownership boundaries, and use that proof during review and publication?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the reviewed product change. I found no actionable correctness or safety defect in the pinned diff. I have no unresolved objection to this change proceeding through the remaining release qualification gates.

Reviewed program commit: `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`.

Compared base: `88dd933877ac7dce2da1cce799e4b00063423299`.

Pull request: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/27

This verdict covers the source change and the local controls below. It does not certify unfinished guest installation, recovery, disconnected restore, development acceptance, publication, or production deployment.

## Scope and findings

I read `release_baseline.py`, its callers in `release_plan.py` and `release_worker.py`, the new archive tests, and the changed neighboring fixtures. I also read the underlying native planner, baseline implementation, active release receipt verification, prior-source checks, and durable program transaction checks.

The measured omission is consistent with the existing implementation. VersionDrift tracks selected native roots and does not include `LIFEOS/HERMES/`. The system file planner does include the broader `LIFEOS/` root. A changed `LIFEOS/HERMES/LogAnalysis.ts` therefore collides when its installed bytes have no recorded baseline hash. The repair does not infer ownership from the current installed bytes alone.

1. Exact archive provenance: `release_baseline.py:17` requires a verified active release and exact version, 40-character commit, and 64-character archive hash. The accepted source must have the fixed `lifeos/LifeOS/install` layout. The helper selects a retained archive from either the exact version-and-commit cache directory or the profile-bound managed operation download. It hashes the opened archive before it reads archive members. The expected digest comes from the current verified integration receipt through `inspect_operation`, not from the candidate release or the omitted file itself.

2. Preservation of baseline entries: `release_baseline.py:55` examines only desired non-generated program paths that the recorded baseline omits. It leaves all recorded hashes intact. The helper returns a copied mapping with proven omitted hashes. It does not save that mapping or change the installed baseline file. Existing baseline entries continue through `plan_system_files` and retain their original drift refusal.

3. Preservation of later edits: the omitted installed file must match the exact corresponding prior archive member. A changed owner file therefore has no accepted proof. After augmentation, the actual native planner checks the installed file again against its accepted hash. My publication-plan probe confirms that a later edit raises `UpdateConflict` before a program publication plan can succeed.

4. Path and owner boundaries: the native planner checks the installed path components and excludes `USER` and `MEMORY`. The archive path must have a canonical physical parent. The archive must be a single-link regular file owned by the current user without group or other write access. The final component opens with `O_NOFOLLOW`. The new helper does not change the profile selection, installation lease, admission, owner grant, or account launcher checks in its caller.

5. Archive bounds and races: the helper enforces the existing archive size, expanded member size, and member count bounds. It rejects duplicate or nonregular matching entries. It checks the opened descriptor identity and timestamps before and after parsing, compares the retained pathname to the descriptor, and hashes the archive again. My probes mutate the archive after its initial digest and replace it with equal bytes at a different inode. Both cases refuse.

6. Review and publication integration: `release_plan.py:76` augments the baseline before computing native changes. It places the augmented mapping in `selected['reviewed_baseline']`. `release_worker.py:216` uses this selected mapping in `_program_plan`. The admitted worker calls `inspect_operation` again before applying the programs. The existing program transaction records exact before and after identities and refuses edits after preparation. This source change does not replace those checks.

7. Existing candidate-equal omitted bytes retain the previous behavior. The helper does not require an archive if an untracked installed file already equals the desired candidate file. The underlying planner already accepts this case without replacing the file. The repair does not introduce this allowance.

## Independent verification

I ran the following suites with the specified frozen Python environment and `-W error::ResourceWarning`:

- `test_release_baseline`
- `test_release_accounts`
- `test_release_configuration`
- `test_release_programs`
- `test_release_operation`

Result: **63 tests PASS**, 64.309 seconds, no skips. Full command and output are retained beside this report.

The archive helper tests use real synthetic tar archives and filesystem entries. Some neighboring unit tests substitute service and planner boundaries. These are unit controls, not end-to-end installation claims.

I also wrote and ran `probe_baseline.py`. Result: **13 cases PASS**:

- Four invalid accepted-release identities refuse.
- The archive byte, expanded byte, and member count limits each refuse.
- An unsupported source layout refuses.
- A personal-data destination refuses.
- A source parent alias refuses.
- An archive append after the first digest refuses.
- An equal-byte archive replacement at a different inode refuses.
- The actual publication planner accepts a proven omitted native file, prepares a durable transaction, refuses the same collision when the augmentation is removed, and refuses a later program edit.

The last probe uses the actual `_program_plan`, native system planner, hook and dependency modules, configuration subprocess, and `ProgramTransaction.prepare`. It uses synthetic local program files and no live guest. Its module provider exposes those real modules through the current bridge interface. It does not claim actual guest execution.

The archive race probes patch only the digest call boundary to introduce a measured filesystem change after the first real digest. The bounds probes lower the real bounds for small test archives. These probes do not replace archive results or simulate a successful proof.

## Release claims and remaining gates

The inspected candidate metadata identifies version `0.5.0`, commit `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, and archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`. It records `combined_release_verified: false` and `live_selection_changed: false`. The progress file leaves unfinished qualification gates pending. I did not treat the earlier archive's passing test counts as qualification of this replacement archive.

The older installed manager's HTTP review uses its installed planner. Updating the manager through the native plugin command is therefore an explicit migration prerequisite for this older installation. This review does not certify an uninterrupted one-click update directly from the old manager. The primary agent continues the real guest bootstrap, apply, and recovery tests.

I did not run a remote command, read personal records or credentials, call memory or journal tools, edit product code, commit, push, or merge. I wrote only the review artifacts.

## Artifacts

- `reviewed-diff.patch`: exact reviewed product and test diff.
- `release-baseline-numbered.txt`: numbered helper source.
- `targeted-tests.stdout` and `targeted-tests.stderr`: complete test output.
- `commands.txt`: reproducible test and probe commands.
- `probe_baseline.py`: independent probe source.
- `probe-results.json` and `probe.stderr`: full probe result and error output.
