Date: 2026-10-15
Role: Independent release preservation reviewer
Question: Why does the post-owner-remount daily verifier reject the sealed release targets, and what bounded evidence can verify the generated baseline without weakening later-edit protection?
Model: gpt-6.1-sol, high reasoning effort

## Conclusion

The primary's measured single-file mismatch is consistent with the actual release and native mount code. It is not a directory overlap. The release program transaction records the pre-mount VersionDrift baseline fingerprint. The release's native mount then publishes a newly generated baseline as an eighth mount entry. The later authenticated owner remount records its normal seven output files and does not regenerate or record the baseline. Consequently the current seven-file override map cannot account for the baseline that the release already generated.

This explains a verifier boundary error. It does not justify rebinding an old journal, replacing the baseline, accepting arbitrary current fingerprints, or weakening the product restore refusal. The initial 221-target release verification remains a historical post-apply checkpoint. The later owner journal must remain authoritative for its own seven files.

A narrow evidence-only baseline proof is possible if it independently derives the expected baseline metadata and complete program file map from the immutable qualified package and authenticated deployment inputs. No implementation of that proof was reviewed in this report. Its guard code and negative controls require closure before it can admit a new backup verification.

## Evidence scope

The actual guest diagnostic is the primary's read-only measurement, not a remote check performed by this reviewer. The primary reported all 221 entries checked with exactly one mismatch, index 207: the default VersionDrift baseline file outside the installed root. The recorded program after fingerprint begins 352ad6ad and the current fingerprint begins c39458b7. Both modes are 0600. The current owner journal has seven outputs. The initial release journal had eight outputs and the initial release verifier passed all 221 targets. The failed backup attempt did not create an archive and recovered all three source services.

parent-measured-summary.json preserves this provenance. I inspected local public source and public package data only. No live baseline, private map, remote host, credentials, personal source, or memory record was read. No product, policy, journal, baseline, or operator source changed.

## Exact code path

In optional/lifeos_release_manager/release_worker.py, _program_plan selects the existing baseline file as a program source when native_changes is true. ProgramTransaction therefore records that file's earlier fingerprint as its program after state.

During application, programs.apply completes before the native mount. The worker then calls create_baseline with package/lifeos/LifeOS/install and the selected installed root. It serializes that generated value and passes baseline_data to mount.execute with the release binding and retain_for_rollback true. MountTransaction appends the baseline as an additional output only when baseline_data is supplied. Its normal FILES tuple has seven outputs.

The original release recovery checker reads the release-bound eight-entry mount journal, verifies the native outputs, and supplies all eight exact file overrides to ProgramTransaction.check_applied. That is why the actual initial release verification can pass even though the baseline program entry alone still records the earlier file fingerprint.

A later owner remount does not supply baseline_data. It publishes and records the seven normal profile outputs, uses the legitimate owner journal rather than the earlier release binding, and does not authorize the old release restore. The new daily current-owner verifier correctly checks that later journal and obtains seven file overrides. Its call to check_applied then compares the generated baseline to the earlier program after fingerprint and refuses.

The current owner mount does not normally write a child of a program directory target. _program_plan directory targets are the bridge, manager, and selected native dependency directories. MountTransaction FILES are config.yaml, SOUL.md, .env, and the four profile plugins/lifeos files. The measured baseline is a separate direct file target. A directory exception is neither needed nor supported by this diagnostic.

## Independent checker characterization

Six local characterization cases execute the actual ProgramTransaction.check_applied and fingerprint functions against real synthetic files. Only the _load boundary supplies synthetic entry metadata. No guest receipt or live journal is involved.

1. An unchanged release passes.
2. An exact direct-file owner-mount override passes.
3. A changed file under a directory target does not gain authority from a child-file override. It refuses.
4. An unrelated added file inside a directory refuses.
5. A changed retained before-i file refuses with the distinct retained-program error.
6. A blind override using the current directory fingerprint accepts an unrelated added file. This is the unsafe boundary demonstration, not a recommended fix.

All six cases behave as expected. Raw data and probe code are retained in program-mount-semantics.json and the associated stdout, stderr, and check_program_mount_semantics.py. The product checker itself needs no change for the measured baseline issue.

## Requirements for a bounded generated-baseline proof

The proof should admit exactly the expected default baseline path derived from the operation's selected installation. It should require a regular owner file, private expected mode, no link redirection, and the exact sealed baseline entry. Its retained before-i fingerprint must remain checked.

The proof must derive expected values independently of the live baseline:

- schema must be the native schema 2 with the exact expected field set.
- version is the public native LifeOS version, 7.40.4. It is not the integration version 0.5.0.
- source_commit is the archive-authenticated native Git HEAD, 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c. It is not the integration program commit 04efe633.
- source_root is the exact operation package/lifeos/LifeOS/install path. The actual worker call uses this path, not runtime.reference.
- installed_root must equal the exact selected and resolved operation installation.
- files must contain the complete independently derived deployed eligible file set and its authenticated expected hashes.

The complete key set is essential. Checking only hashes for keys that happen to exist in the live baseline allows omitted entries. Checking only present reference files against public source also allows deleting the same file from both the reference and baseline. The reference inventory itself must be authenticated or independently derived from the exact archive's deterministic deployment rules.

A local public-only measurement found 1,757 candidate paths under the native tracked CORE_PATHS selector plus its two fixed plugin-source exceptions: 955 skill files, 689 LIFEOS files, 98 hook files, seven commands, and eight agents. Native DeployCore and InstallHooks deploy skills, LIFEOS, and hooks. The 15 agents and commands are not deployed by those install stages. That leaves 1,742 candidate deployed keys before verified installer or dependency differences. These counts describe public candidates, not an asserted live baseline inventory. public-source-baseline-candidates.json retains the exact public candidate map and that warning.

Six eligible source paths are bun locks. Where the qualified reference lock differs from the raw native payload, the proof must use an independently authenticated dependency catalog or sealed program entry hash. It must not accept an unexplained reference difference or substitute the live installed hash as its expected value.

After validating the complete semantic baseline, reconstruct the exact expected worker serialization and its file fingerprint. Supply that one independently proven baseline override along with the seven strict current owner mount outputs. Keep all remaining 220 program targets and every retained before-i identity strict. Do not broadly override native program files or directories.

## Timestamp and byte preservation limit

create_baseline sets created_at from the wall clock. The native baseline fingerprint helper excludes created_at, but the program file fingerprint includes it. The old operation status contains no timestamp, and the earlier eight-entry journal is no longer available through the current owner journal.

A proof must require a strict integer timestamp, not a Boolean, and use an independently retained apply or observation window if available. The actual default public daily application necessarily follows its public release selection, which may supply a lower chronology bound. The proof must state which measured bounds it uses.

Without an independently retained original timestamp or digest, the proof cannot claim that created_at retains its exact original value. A semantically valid generated baseline with a bounded timestamp is a different claim from exact historical byte preservation. If the proof uses the current timestamp field to reconstruct canonical bytes, that scope must remain explicit. It must not silently treat a live fingerprint as historical authority.

## Required negative controls

Before using the evidence helper, its controls should refuse:

- A wrong or unverified public archive, source identity, operation, selected installation, or baseline path.
- A symlink, wrong ownership, shared write access, or wrong baseline mode.
- Missing, extra, or wrong schema fields and wrong native version, native commit, source root, or installed root.
- One omitted baseline path, one extra path, one changed digest, or a noncanonical generated serialization.
- A public file omitted from both the reference and baseline.
- An unexplained reference or installed program byte difference.
- An unbound, invalid, future, Boolean, or out-of-window timestamp according to the documented chronology rule.
- An unrelated changed program target, changed retained before-i file, or changed current owner mount output.

The positive case must use real qualified public inputs and the actual safe captured metadata, not a constructed guest completion receipt. The final real restore remains pending until actual execution produces its own backup, restored map, program checks, and cleanup evidence.

## Concrete plan assessment and independent public catalog

The primary subsequently measured the actual baseline as exactly 1,742 keys. Relative to the raw public tracked candidate map, the only missing paths are the 15 agents and commands paths that the native installer does not deploy. The only changed payload hash is skills/Telos/DashboardTemplate/bun.lock, which the authenticated native dependency catalog replaces. These are primary guest observations, not personal baseline reads by this reviewer.

I independently reconstructed the proposed public map from the actual immutable archive. I verified the archive SHA-256, compared the public cached Git index and HEAD to the archive copies, checked every selected source file's bytes against its archive member, and verified all 12 dependency catalog lock entries against the actual archived lock bytes. The deterministic deployed prefix selection yields exactly 1,742 keys without using live or reference key sets.

Five catalog bun.lock paths occur in this baseline map. A sixth eligible tracked lock, LIFEOS/TOOLS/Transcribe-bun.lock, is not a catalog package bun.lock and retains its native archive hash. Only the Telos DashboardTemplate lock changes: payload digest 44ed2719c7202a9ceb5d0d073b11eb9774386a483ee7e54e07d3b1d68dd0c939 becomes qualified digest 6730998376137590a083fd4334a21693c0821f93a29766dd07dd9643a8d818f7. The canonical complete file-map digest using sorted keys and compact separators is 5deab51ef78b77e0d577b97f94428d8d13337c7cfdcde75c9e9a93c7e3746b92. The full public map and checks are retained in independent-public-generated-baseline-catalog.json.

The concrete helper plan now satisfies the conceptual objections: it derives this complete map from the authenticated archive, pins its digest, validates exact schema, native version, native source commit, source root, selected installation, private mode, and canonical serialization, and reconstructs one expected baseline fingerprint. It retains all other program and native journal checks. It also captures the source baseline digest for exact comparison after actual restore.

The timestamp plan uses a strict integer bounded below by actual public publication and above by the original apply mount-intent file mtime plus one second. The stated scope correctly treats this as bounded metadata rather than proof of the exact original timestamp. The mount-intent file should remain bound to the same operation and apply action and should be a regular owner file. Its mtime is a chronology observation, not immutable timestamp authority.

Two implementation checks remain necessary: select exactly one sealed file entry for the expected default baseline target, and refuse any collision with the current seven owner mount override keys. The helper must not silently replace an unexpected current native output. The code and negative controls are still pending review. This addendum approves the bounded plan, not an unseen implementation or a new real restore result.
