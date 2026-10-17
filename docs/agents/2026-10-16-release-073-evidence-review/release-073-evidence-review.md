# Release 0.7.3 qualification evidence review

- Date: 2026-10-16
- Role: independent evidence reviewer (Claude Code, single agent, no delegates, no memory or journal calls)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Question: Is the committed 0.7.3 qualification evidence at `2fa3d516` accurate, internally consistent, and clear to a public reader? Does any release claim lack a measurement?
- Scope: `docs/verification/2026-10-16-release-0.7.3/`, the committed PR38 review and repair reports, and Git objects `70fa8390`, `03d6f486`, `050a4e19`, `403c5f48`. Only digest, JSON, Git, and text checks. No native suite reruns.

## Verdict

**No blocking finding. No unsound release claim.** Every hash, count, digest, and equivalence claim that I checked matches the raw evidence. Four LOW findings remain. They are provenance and wording gaps. None of them changes the qualification result. Because they are actionable, the verdict is not CLEAR in the strict sense. If Adrian treats LOW documentation items as non-actionable for this snapshot, the result is CLEAR.

The published certificate is an immutable release asset (digest `d4b002d3...`). Each correction below goes into the pending deployment README or a sidecar file. None of them requires the certificate to change.

## What I verified

| Claim | Evidence | Result |
|---|---|---|
| Ten `qualification_receipt_sha256` values (`RELEASE-CERTIFICATE.json:50-61`) | `sha256sum` of the JSON files and of each decompressed `.gz` | All 10 match |
| Certificate asset digest and size (`release-publication.json:23-27`) | Local certificate: sha256 `d4b002d3...`, 4225 bytes | Match |
| Archive asset digest and size (`release-publication.json:11-15`) | Certificate lines 7-8, `package-identity.json:4-5`, integration JSON lines 4-5 | Match |
| Dashboard asset digest (`release-publication.json:20`) | Certificate line 9, and the 0.7.2 certificate value | Match, unchanged from 0.7.2 |
| Inherited 0.7.2 certificate sha256 (line 43) | `git show 403c5f48:docs/verification/2026-10-16-release-0.7.2/RELEASE-CERTIFICATE.json` | `96e45a46...`, match |
| Prior archive sha256 (`package-verification.json:71`) | 0.7.2 certificate `archive_sha256` | `293cfa2c...`, match |
| 1129 executed, 1126 passed, 2 errors, 1 failure (lines 33-36) | Decompressed integration stderr: 1129 unique test headers, 1122 inline `... ok` plus 4 `ok` lines split by interleaved output, summary `Ran 1129 tests`, `FAILED (failures=1, errors=2)`, 0 skips | Match |
| Three environment-specific results | Socket `AF_UNIX path too long` (test_profile_backup), `PermissionError /proc/814420/exe` (test_removal_consumers), `sshd-session` refusal (test_removal_coordinator) | Match |
| 35 short-TMPDIR backup cases (line 40) | `socket-path-short.txt`: `Ran 35 tests`, `OK`. The full run has exactly 35 `test_profile_backup` cases | Match. `profile_backup` files are absent from the 0.7.3 changed list, so "unchanged" holds |
| Long-path reproduction | `socket-path-long.txt`: the same case, `OSError: AF_UNIX path too long` | Match |
| 8 isolated boundary cases (line 38) | The full run has exactly 8 cases in the two modules. `primary-boundary.json` exit 0, status PASS. Six source hashes equal the `70fa8390` and `03d6f486` blobs | Match (see F3 for the binding limit) |
| Import 116, UI 57, focused 51 (lines 30-32) | `archive-import-smoke.txt`, TAP `# pass 57`, `Ran 51 tests ... OK` | Match |
| Source and runtime equivalence (lines 17-28) | `git diff 70fa8390 03d6f486`: only `docs/agents/`, `notes/`, and one test file change. `ast.dump` of both test versions is equal. `notes/` is not in the packaged changed list | Match |
| Commit ancestry | `70fa8390` is an ancestor of `03d6f486`, which is an ancestor of `403c5f48`. `03d6f486..403c5f48` changes only `docs/agents/` | Match |
| Three CLEAR rounds | r1 CLEAR at `99e18c44`, r2 CLEAR at `70fa8390`, r3 CLEAR for `70fa8390..03d6f486`, all `claude-opus-5-5`. `review-verification.json:9` equals the sha256 of the r3 report at `050a4e19` | Match |
| First-attempt history | Repair `repair-summary.json` and `archive-integration-99e18c44.stderr`: 1128 run, 1123 pass, 3 errors, 2 failures. Four `Errno 122` lines. 100 probe rounds, 12 nonterminal at return, maximum 4.18 ms. Mutation detected | Match. Preserved in the repair report |
| Six native Git metadata deltas (line 44) | `package-verification.json:72-79` | Match |
| Published versus pending deployment | Certificate lines 63-64 and `PROGRESS.json:2,13-14` keep promotion false while status is published and qualified | Distinguished correctly |
| Single clean full run | Certificate line 37 and `PROGRESS.json:20` are false | Correct |

## Findings

### F1. LOW. The certificate does not bind the raw log that supplies its integration counts

- Location: `docs/verification/2026-10-16-release-0.7.3/RELEASE-CERTIFICATE.json:50-61`, against lines 33-36.
- Measured cause: the receipt map hashes `archive-integration-70fa8390.json`. That JSON records only `exit_code: 1` and `status: FAIL`, with no test counts. The counts 1129, 1126, 2, and 1 exist only in `archive-integration-70fa8390.stderr.gz`. The certificate does not list that file. No other committed file records its sha256. Commit `2fa3d516` binds it in Git. The published certificate, as a standalone asset, does not bind it. The 0.7.2 certificate has the same gap.
- Minimal correction: in the deployment README, record the decompressed stderr sha256 `f3d817c84afedccd8b8da7180182e1f762126d6a625107d7e67c5e183a9585fc` (213465 bytes) and the `.gz` sha256 `a34f741d6a10f7bb9d74803e2710aa38edc6a837cc7b4a9fcb2d09727bfce2d8`. Add the stderr log to the receipt map of future certificates. Do not re-publish this certificate.

### F2. LOW. The socket replay receipts do not record the TMPDIR or the filesystem they describe

- Location: `RELEASE-CERTIFICATE.json:41`, "with a short private TMPDIR on the same filesystem".
- Measured cause: `socket-path-short.txt` and `socket-path-long.txt` contain only unittest output. Neither records the command, the TMPDIR value, or the device. The long full-run TMPDIR is recorded (`archive-integration-70fa8390.json:135`, 69 characters). The short TMPDIR value and "same filesystem" are therefore stated, not shown, in the copied receipts. The `AF_UNIX path too long` error itself proves that the long socket path exceeds the limit, so the cause attribution is sound.
- Minimal correction: in the deployment README, give the short TMPDIR path and the command for both socket replays. If the filesystem identity was not captured, write "on the same cache directory tree" or delete "on the same filesystem" from the README wording.

### F3. LOW. The isolated boundary receipt binds six files, not the full imported source

- Location: `docs/verification/2026-10-16-release-0.7.3/qualification/primary-boundary.json:8-15`, which supports `RELEASE-CERTIFICATE.json:38,45`.
- Measured cause:
  1. The receipt hashes six files. `tests/test_removal_coordinator.py:41-42` at `70fa8390` also imports `removal_preparation._consumers` and `release_programs.publish`. The receipt does not hash these two modules.
  2. The receipt records no source commit and no digest for the source tarball. The committed operator (`docs/agents/2026-10-16-codebase-cleanup/primary-evidence.tar.gz`, `account_boundary.py:43,49`) extracts `boundary-source.tar` and uses Hermes from the 0.7.2 package directory, not the 0.7.3 archive.
  3. The raw unittest output of the `lifeos-073-test` run is not in the 0.7.3 directory. The operator sets PASS only if the output contains `Ran 8 tests`, ends with `OK`, and has no skips (`account_boundary.py:93`). That operator copy is the cleanup-era variant (account `lifeos-cleanup-test`). The 0.7.3 variant is not committed.
- Why the claim still holds: Git history shows that `removal_preparation.py` and `release_programs.py` last change at `a4c93955`. Between `a4c93955` and `70fa8390`, no product Python file changes. `package-verification.json` shows that `hermes/` program files are unchanged from 0.7.2. So the equivalence is very likely, but it is inferred from history, not measured by the receipt.
- Minimal correction: in the deployment README, say that the replay ran from a source tarball with six hashed files and with the 0.7.2 Hermes tree. If the replay stderr and `boundary-source.tar` still exist in the cache, copy the stderr into the release directory. Then record the tarball sha256 and a full file-hash comparison against `70fa8390`. If they do not exist, state the inference from Git history plainly.

### F4. LOW. "Two named workstation failures" conflicts with the certificate's own counts

- Location: `RELEASE-CERTIFICATE.json:45`, against lines 35-36.
- Measured cause: line 36 records 1 failure and line 35 records 2 errors. Line 45 calls the process-inspection cases "two named workstation failures". They are one error (`test_removal_consumers.RemovalConsumersTests.test_running_bun_outside_reviewed_service_groups_refuses`) and one failure (`test_removal_coordinator.RemovalCoordinatorTests.test_exact_running_coordinator_is_admitted`). The certificate does not give the names. A public reader cannot tell which two of the three non-passing cases line 45 means. The text is inherited from the 0.7.2 certificate.
- Minimal correction: in the deployment README, name both cases and call them "one error and one failure". Say that the third non-passing case is the socket error explained at line 41. Use the same wording in future certificates.

## Notes (no correction needed for this snapshot)

- N1. The "non-dumpable" attribution at line 45 is inherited. The measurement is in `docs/verification/2026-10-16-http-memory/integration-verification.json:17`. The 0.7.3 log independently shows the `sshd-session` refusal for the coordinator case. For the consumers case, it shows `Permission denied: /proc/814420/exe` but does not name the process. The README can mark the cause as inherited, with that link.
- N2. `review-verification.json:18` (`full_archive_integration_pending: true`) is a review-phase snapshot, and the certificate hashes it. It is historical, as the brief states. The README is the correct place to explain that the integration run completed after that receipt.
- N3. The repair report and the corrected note (`notes/2026-10-16-process-exit-observation.md`) do not attribute the `EDQUOT` errors to the source exports. The note says the contribution is "plausible but not measured". This is correct.
- N4. The integration receipt has status `FAIL` while the certificate says `QUALIFIED`. The certificate explains all three non-passing cases with separate passing evidence and sets `single_clean_full_run: false`. The qualification is honest coverage across three environments: the workstation full run, the short-TMPDIR backup replay, and the isolated service-account replay.

## Limits of this review

- I did not rerun any suite, contact GitHub, or read the cache. Release asset metadata comes from `release-publication.json`, not from a live API call.
- I checked the boundary-replay operator logic only in its committed cleanup-era copy.
- Raw data: `data.json` in this directory.
