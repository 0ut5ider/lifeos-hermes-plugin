Date: 2026-10-15
Role: Independent release preservation reviewer
Question: Does the implemented public baseline proof admit only the one generated baseline, retain all other preservation checks, and allow a read-only Atlas preparation retry without consuming the source fixtures?
Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the current evidence-only baseline catalog, proof helper, daily verifier integration, Atlas preparation receipt helper, and Atlas reuse branch. No unresolved actionable finding remains in these scopes.

The primary corrected the measured missing-current-mount-output guard and the Atlas Boolean/integer equality gap. Independent closure controls pass. The product release checker, native owner journal, baseline bytes, policy, immutable release archive, and initial certificate require no changes.

This verdict does not claim that the final backup retry, actual archive, restored runtime map, restored Atlas cases, or disposable guest cleanup already succeeded. Actual execution must produce those results. This reviewer ran no remote commands, memory or journal tools, owner API approvals, or live memory reads, and made no source, Git, or policy changes. All writes are reviewer artifacts.

## Brief, initial failure, and reviewed inputs

The primary requested a focused review of build_daily_baseline_catalog.py, daily-baseline-public-programs.json, prove_daily_baseline.py, check_daily_baseline_controls.py, and the integration in verify_daily_restored_programs.py. The primary then added prepared_atlas_evidence.py, its controls, and the --prepared-atlas-evidence branch to this scope.

The measured baseline authority problem and independent public map reconstruction remain in docs/agents/2026-10-15-daily-current-mount-conflict/. The safe daily-recovery-initial-failure.json confirms the first actual attempt stopped at capture-current-owner-mount before backup-source, and its recovery command returned exit 0. The receipt reports one generated-baseline conflict among 221 targets, no archive, and recovered source services. I read only that safe receipt and local source, not the live baseline or private program map.

Exact reviewed source snapshots and their hashes are retained in source/, source-sha256.json, atlas-reuse/, and atlas-source-sha256.json. The catalog rebuild output is retained separately in catalog-rebuild/. The full raw control output remains beside the probe scripts.

## Independently authenticated catalog

I reran the actual builder in an isolated review output directory. It reads the real immutable public archive and produces exactly the same catalog bytes as the proposed committed file. Its digest is 9e3271df325328090fe525b397bbae389fb3806f854d773d98d0a88895194e47. Its complete map equals the independent prior archive reconstruction byte-for-byte at the data level.

The catalog contains exactly 1,742 deployed eligible public program paths. The source native version is 7.40.4 and the source native Git base is 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c. The archive digest is a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813. The map digest is 5deab51ef78b77e0d577b97f94428d8d13337c7cfdcde75c9e9a93c7e3746b92.

The builder selects tracked eligible native files and the two fixed plugin exceptions under the deterministic deployed LIFEOS, skills, and hooks prefixes. It does not use a live baseline or mutable reference key set. It authenticates all 12 archived dependency catalog lock files. Five catalog locks occur in this map. Only the Telos DashboardTemplate lock differs from the raw native payload, as recorded in the independent prior proof. A file removed from both a live reference and baseline cannot remove it from this fixed catalog.

## Baseline proof and outer boundary

prove_baseline pins the whole catalog digest and complete file-map digest. It requires the exact baseline field set and compares the complete parsed baseline against independently constructed expected schema, native version, native source commit, operation package source root, selected installed root, and all 1,742 expected hashes. It reconstructs the native JSON serialization plus newline and requires exact byte equality. It hashes those reconstructed expected bytes, rather than using the live file fingerprint as its authority.

baseline_override derives only the default baseline path from the selected installation. It requires the path to resolve without redirection, exactly one matching sealed file entry, and the expected self-source entry. It refuses a collision with current native mount outputs. It requires a regular, single-link, private 0600 owner file.

The apply intent must be a regular, single-link, private 0600 owner file smaller than 4,096 bytes. Its exact fields must describe action apply with a null or valid prior journal digest. Its path is inside the exact operation job that the caller has already bound through cli.operation and validate_plan. The helper checks source and intent file stamps again after proving the expected bytes.

The timestamp is a strict integer bounded by public publication and the original apply intent mtime plus one second. The verifier explicitly states that this is bounded metadata and does not prove the exact original timestamp. The captured source checkpoint includes the proven full baseline digest. A later restored verification must match that checkpoint exactly, including the timestamp bytes that were actually captured. The helper does not claim stronger historical timestamp preservation.

Independent baseline controls:

- The primary's one positive and 15 refusal controls pass.
- The actual outer helper passes one positive and 21 refusal controls.
- Outer refusals cover missing, duplicate, wrong-kind, wrong-source, and wrong-target sealed entries; current mount collision; baseline and intent permissions, links, and ownership; invalid intent action, fields, prior digest, or size; an invalid time bound; and baseline or intent changes during proof.

Most outer controls use real synthetic files. Ownership faults inject only the local getuid boundary. No live file is read and no guest receipt is written. The tests do not substitute for real backup or restore acceptance.

## P2 finding and closure: Require the complete current owner output set

The initial verifier trusted whichever valid entry subset the current native journal returned. The native manifest parser permits a nonempty subset of its allowed file list. Therefore an otherwise valid journal missing one output could pass the caller while the evidence intended to cover all seven current owner outputs.

The primary added a caller assertion requiring exactly seven entries and the exact profile-relative FILES target set. This change remains in the evidence verifier and does not alter native mount policy.

Three independent controls execute the actual native manifest parser and actual caller guards on synthetic journals. The full seven-output journal passes. A six-output journal and an eight-output journal including the baseline both pass the native allowed-target parser and the previous observed caller guard shape, but the corrected evidence guard refuses both. The probe reconstructs the previous caller shape by removing only the new coverage assertion. It does not claim to be a frozen earlier full operator snapshot.

After that guard, the integration adds exactly the independently proven baseline override and calls the unchanged ProgramTransaction.check_applied. Its sealed entries digest, every retained before-i check, and every other 220 target comparison remain active. The native current mount still passes check_completed, and old release restore availability must remain false. No journal is rebound, normalized, or overwritten.

## Atlas preparation reuse closure

The first actual attempt successfully created three synthetic Atlas cases before it refused the baseline proof. Running prepare again would collide with those fixtures, and running verify on the source would consume interrupted recovery state. The new branch instead validates the original successful preparation command and performs a separate read-only source check before draining.

verify_preparation requires the exact successful preparation report, exact CT102 runuser command, exact Python, exact operation package path, and exactly one successful preparation operation. It distinguishes integer exit code 0 from a Boolean. It returns the safe receipt digest and metadata. The reuse and --resume-backup modes are mutually exclusive.

The source preflight requires the exact preparation report, the three known case names and homes, expected captured-file counts, paths confined to their synthetic homes, physical paths without symlink redirection, regular files, exact captured hashes, and exact modes. The result must match the prior safe receipt. The existing preparation and read-only checks run before source draining. This branch does not call native prepare or verify on the source.

I noted that plain dictionary equality would treat archives true as equal to archives 1. The primary made both source and outer report comparisons use canonical JSON equality. That preserves the intended exact safe-receipt binding. This was a metadata guard correction, not a change to the synthetic recovery cases.

Independent Atlas controls:

- The primary's one positive and 14 refusal controls pass.
- Eleven actual source-preflight cases pass. The positive exact synthetic fixture passes. The checker refuses changed bytes, changed mode, symlink redirection, a missing map entry, an outside-home path, wrong prepared home, wrong case, Boolean receipt count, wrong receipt count, and a missing file.

The source-preflight test redirects only the fixed fixture root into a temporary synthetic directory and executes the actual source-check code. It never calls native Atlas prepare or verify. No actual source fixture or personal record is read or changed. Its outputs explicitly describe that unit boundary.

## Scope and next execution

There are 67 passing cases across the primary baseline suite, outer helper suite, current mount coverage suite, primary Atlas receipt suite, and independent Atlas preflight suite. The independent catalog rebuild also passes and matches both the pinned catalog and the earlier public-only map. Raw failures that characterize the corrected guards are preserved where noted; none is counted as a current test failure.

The next authorized action is the actual detached backup retry using the existing successful preparation evidence and a separate output directory. The primary must still obtain the actual source capture, protected archive, disconnected restored checks, exact source-to-restore baseline digest, Atlas cases, runtime artifact map, source service recovery, and owned guest cleanup. This review does not manufacture or preapprove those future results.
