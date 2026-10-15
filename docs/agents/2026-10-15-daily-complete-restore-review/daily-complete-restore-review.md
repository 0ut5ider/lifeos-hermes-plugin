Date: 2026-10-15
Role: Independent release recovery reviewer
Question: Do the daily complete restore operator and current-owner-mount verifier provide safe pre-execution admission, isolation, recovery, and bounded preservation proof?
Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the corrected proxmox_daily_restore.py and verify_daily_restored_programs.py. The three measured findings below are closed. No unresolved finding remains in this bounded source review.

This review does not claim that the daily backup, protected archive, restored guest, Atlas verification, runtime map verification, or disposable cleanup already ran. Those results require actual execution. I did not run remote commands, use memory tools, read credentials or private maps, manufacture guest receipts, or change source operators. Only reviewer artifacts changed.

## Brief and source scope

The primary requested review of an adaptation of the already reviewed whole-guest rehearsal. The daily source is CT102. The owned disposable restore target is CT110 on the existing test storage with a 120 GB root disk. The intended source state is the exact 0.5.0 package after actual daily acceptance, authenticated owner source admission, and editor activation. The operator must preserve the later owner mount and must not rebind the earlier release journal.

The reviewed product remains commit 04efe633296eb2b1a1d95561ca6d3e9516cd47dc, archive SHA-256 a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813. Exact current source snapshots and digests are retained in the two .after.py files and reviewed-source-sha256.json.

## Findings and closure

### P2: The restored verifier invocation omitted its action argument

The initial source read showed the restored command passing only the operation identifier. The new verifier requires action capture or verify followed by the operation identifier. The initial command would stop at argument parsing after the restored artifact verification.

The primary added verify before the operation identifier. The current actual command expression passes the actual verifier parser. A separate check of the original one-argument shape against that same parser confirms refusal with exit 2. The first saved source snapshot already contained the primary's argument correction, so restore-invocation-before.json is not red evidence. snapshot-timing.json states that explicitly. The original argument shape is recorded in original-observed-invocation-parser-refusal.json. A probe setup AttributeError was corrected locally and is retained in invocation-probe-setup-error.stderr.

### P2: Backup continuation could claim source recovery without checking it

The initial --resume-backup branch loaded archive metadata and skipped the source service controller. It left the recovery obligation false and could later report source_writers_resumed true. If the previous attempt completed its backup but failed its normal resume and final recovery, continuation could finish while the daily writers remained stopped.

The retained exact branch controls show all four desired continuation cases failing before the correction because no source check occurred. The primary now sets the recovery obligation before calling the source. The source conditionally resumes the native profile, requires recovery_required false, and checks all three services through actual systemctl ActiveState and SubState values. It clears the obligation only after success. Fresh-run resume and final recovery also check actual active/running states.

All four current controls pass: already running, native recovery required, native recovery still required after resume, and an inactive actual service. The last two refuse and retain the recovery obligation. Exact branch and service-helper AST code runs locally with synthetic failure boundaries. No guest service command runs in these controls.

### P2: Isolation covered only net0 and checked it after boot

The initial operator deleted net0 and later asserted only that net0 was absent. A restored net1 interface could remain attached while the summary claimed network_disconnected true. The first guard was also after boot.

The primary now reads the restored native configuration before mount and boot, deletes every netN interface, disables automatic startup, and refuses any remaining netN or raw lxc.net.* key. It requires onboot 0 and unprivileged 1 before boot. It rechecks the network keys after boot and before owned guest destruction.

All six current local controls pass: one interface, two interfaces, no interface, an interface that remains after deletion, a raw lxc.net.* setting, and a privileged configuration. The latter three refuse before mount and boot. The retained initial source permits the additional-interface case. The controls exercise only the exact preboot configuration block with synthetic Proxmox responses.

## Other reviewed guards

The operator checks the cluster inventory before selecting CT110. It restores only an archive with the CT102 PBS path prefix. It sets and verifies native backup pruning protection. It uses the configured test storage, forces unprivileged restoration and onboot 0, disconnects the guest, and masks all three application services in the mounted root before starting it.

The default source path requires the actual editor activation receipt for the same operation before creating synthetic Atlas fixtures. Those fixtures use isolated synthetic roots outside the personal store. The source profile is drained before current mount and runtime artifact capture. The recovery obligation is set before drain. Normal resume clears it only after verified service state.

The restore path verifies all three archived synthetic Atlas cases, compares the actual restored private runtime map digest and counts against the source capture, and invokes the current-owner-mount program verifier. The map enumerator covers the nine selected runtime roots. The operator exports counts and digests, not the private map. The source programs and personal-data preservation claim distinguishes the explicitly created isolated synthetic fixtures.

The finalizer preserves the first failure when source recovery also fails and always records a failure completion marker. Three additional exact-finalizer controls pass: no obligation, successful obligated recovery, and failed obligated recovery. The failed cleanup adds a note to the original exception. The owned guest is destroyed only after successful verification and shutdown, and only after checking the expected hostname, disposable tag, and disconnected native configuration. A failed rehearsal can retain the owned disposable guest for investigation; that is not a successful cleanup claim.

## Current owner mount verifier

The verifier admits only the exact 0.5.0 request and applied operation. It validates the sealed plan and requires a non-fresh native mount. It checks the current committed native mount, requires no earlier release binding and no retained rollback mode, and requires the earlier operation restore to remain unavailable.

The current native mount entries provide explicit expected fingerprints for the sealed program transaction check. This verifies the later legitimate owner mount without changing the earlier journal. The source capture records the current journal digest, complete profile configuration digest, Pulse user configuration digest, and original service unit digests. Restored verification requires the same checkpoint, actual /dev/null masks, and identical saved original unit bytes.

The verifier checks the two prepromotion private configuration digests without exporting their values, preserves the selected model and tiers, requires the exact editor activation output configuration, and retains the enabled normal 07:00 morning schedule. It checks the current installed package again before printing PASS. It does not enable the earlier release restore and does not modify personal records.

## Retained evidence and limits

The raw current and initial control outputs are in this directory. Current control groups are one actual command/parser agreement, one original argument-shape refusal, four continuation cases, six isolation cases, and three finalizer cases. All current controls pass. The local fault boundaries do not stand in for a real protected backup or restore.

The primary must still collect the actual protected archive metadata, actual Atlas cases, actual restored map and program checks, actual source service recovery, and actual owned guest removal. A PASS result from this review is permission to proceed within the authorized workflow, not evidence that those operations have completed.

## Retained public asset guard addendum

After the initial CLEAR, the primary added read-only checks for the retained public download archive and certificate. I reviewed that narrow addition. It hashes the actual retained package archive, checks the immutable initial certificate digest, and compares the parsed certificate to the exact sealed request certificate. The report adds retained_public_archive_and_certificate_verified only after those checks. No recovery authority or journal binding changes.

Six independent actual-assertion cases pass using the real public archive and initial certificate bytes: the public positive case, altered archive, altered certificate, changed request certificate, missing archive, and missing certificate. All negative cases refuse. The current reviewed verifier SHA-256 is 777c03663bdf8c5fc015868678b9cd76eda47d484edbf168f5fc159bf680830a. The exact current source and raw results are verify_daily_restored_programs.archive-guard-closure.py, retained-public-asset-controls.json, and retained-public-assets.stdout and stderr. The verdict remains CLEAR for this addition. Actual restored asset survival still requires the real guest verification.
