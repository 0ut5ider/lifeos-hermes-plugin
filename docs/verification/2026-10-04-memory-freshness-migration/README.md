# Native freshness migration publication

Date: 2026-10-04. This unit covers constitutional context migration and current/ideal state membership stamping. It uses synthetic source files. Production remains unchanged.

The [baseline](before-output.txt) reports ten failures, six passed parent tests, and nine passed subtests. Three parent failures cover read-only context writes, read-only state writes, and a foreign backup directory. Seven subtest failures cover public file permissions. The [baseline test source](baseline-test-source.py) matches the recorded baseline hash.

The bridge supplies admitted current source bytes to the original transformations. The renderer keeps source bodies, frontmatter rules, SHA-256 checks, seed timestamps, derived-source metadata, console reports, and state membership fields. Context migration does not read the excluded TELOS target. Read-only owners can preview. Apply requires unrestricted owner write authority and current configuration.

The publication journal covers source changes and the original-byte backups together. The system publisher permits only the three fixed context files and their exact native backup names. Redirected user or system backup directories and registry aliases refuse before journal collection. Source changes and owner revocation after actual rendering refuse publication. Actual process exits after user and system publication recover all previous source and backup bytes.

Managed apply preflights the whole native result before writing. A missing, excluded, or malformed required context source blocks the apply operation. The bridge does not publish successful files from a failed batch or return an unperformed `WROTE` report. Standalone LifeOS keeps its original partial-failure behavior. This is an intentional managed publication difference.

The first candidate gate passes 13 tests and 16 subtests. The expanded gate passes 20 tests and 19 subtests. The [large-source control](large-before-output.txt) then fails. Seven files below the per-file limit produce 14 native publications because the renderer returns sources and backups. The [measured result](large-measurement-before.json) contains 3,447,548 bytes, above the input corpus limit despite valid source sizes.

The render bound now accounts for both serialized source copies and report metadata. The console response keeps its separate corpus bound before publication. The [corrected control](large-after-output.txt) passes, and the [actual receipt](large-measurement-after.json) commits all 14 artifacts. The corrected focused gate passes 21 tests and 35 subtests. It includes complete ASCII and UTF-8 bodies and original-byte backups.

The [final combined gate](final-output.txt) passes 212 tests and 152 subtests without failures, errors, skips, or warnings. It includes migration, timestamp/cache publication, freshness reads, service operations, native facts, state and summary publication, source review, registry aliases, native/profile recovery, source preparation, patch packaging, and footprint checks. Exact commands, environment, source hashes, and the pinned source manifest are in [final-command.json](final-command.json).

All [23 recorded native controls](controls-output.txt) pass. Large synthetic source bytes use SHA-256 named [source blobs](native-outcomes/source-blobs), with matching hashes in the case records. Four controls also compare the original native console reports with the scratch pure renderer. All 38 [distributed native files](distributed-comparison.json) match the scratch source, and both patch copies are equal. The [Bun build](build-result.json) passes. Bundling does not validate TypeScript types.

Interview evidence and reminder callers, other derivative publishers, aggregate service recovery, restricted delivery, ownership activation, and the combined release remain open. This unit retains the cooperative writer boundary. It does not protect against hostile same-UID filesystem replacement between the final path check and publication.
