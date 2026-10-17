# Release 0.7.3 qualification evidence review, round 2

- Date: 2026-10-16
- Role: independent evidence reviewer (Claude Code, single agent, no delegates, no memory or journal calls)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Question: Do the provenance fixes at `3008300fd5ca4b25243a36a49d1545b6a39a4d24` close the four LOW findings F1 to F4 from round 1 (`docs/agents/2026-10-16-release-073-evidence-review/`), without a change to the immutable initial certificate?
- Scope: `docs/verification/2026-10-16-release-0.7.3/` (with the new `QUALIFICATION-PROVENANCE.json`, `qualification/PROVENANCE.md`, and five new compressed records) and `CONTRIBUTING.md`. Only digest, Git, JSON, and text checks. No suite or unit reruns, no SSH, no browser, no credentials. Read-only digest checks of the local release cache at `~/.cache/lifeos-release-0.7.3-20261016/`.

## Verdict

**CLEAR.** All four responses are true against the files. Every digest, count, and byte size in the supplementary receipt reproduces. The Hermes program map digest and the boundary source tar digest reproduce independently from the published rules. The initial certificate is unchanged (sha256 `d4b002d3...`, 4225 bytes, no Git change since `2fa3d516`). No gap remains that needs a fix.

## Change inventory

`git diff --stat 2fa3d516 HEAD` shows only these changes: `CONTRIBUTING.md` (one line), `QUALIFICATION-PROVENANCE.json`, `qualification/PROVENANCE.md`, five new `.gz` records, and the round 1 review files. The working tree is clean for these paths. `3008300f` adds only `hermes_program_map_sha256` and `hermes_map_reconstruction` to the receipt. The committed receipt is byte-identical to the cache copy that will become the release asset.

## F1. Integration log binding: CLOSED

| Claim (`QUALIFICATION-PROVENANCE.json:10-20`) | Independent result |
|---|---|
| compressed sha256 `a34f741d...` | match |
| raw sha256 `f3d817c8...`, 213465 bytes | match, 213465 bytes |
| 1129 tests, 2 errors, 1 failure, 0 skipped | log line 1173 `Ran 1129 tests`, line 1175 `FAILED (failures=1, errors=2)`, 0 `skipped` strings |
| 1126 passed | 1129 minus 3 |

`PROVENANCE.md:5` repeats the same values.

## F2. Socket replay provenance: CLOSED

- Both new outputs hash to the recorded raw and compressed digests (`QUALIFICATION-PROVENANCE.json:62-63,84-85`).
- The long replay output reproduces `OSError: AF_UNIX path too long` at `tests/test_profile_backup.py:376`, `Ran 1 test`, `FAILED (errors=1)`. Exit 1 agrees.
- The short replay output has 35 `... ok` lines, `Ran 35 tests`, `OK`. Exit 0 agrees.
- Each new output is identical to the original `socket-path-*.txt` copy except the elapsed time line.
- TMPDIR lengths are 69 and 34 characters, as recorded. The long TMPDIR and the working directory equal the full-run record (`archive-integration-70fa8390.json:9,135`), so the replays use the qualified package extract.
- Timestamps are sequential: long ends at 00:15:52.142122, short starts at 00:15:52.142304, receipt `observed_at` is 00:16:29.
- I measured `st_dev` for both directories today. Both are 38, which agrees with `device: 38` and `socket_directories_same_device: true`.
- `PROVENANCE.md:17` says plainly that the filesystem measurement belongs to the new replays and is not inferred from the earlier unrecorded commands. That statement is honest.

## F3. Boundary replay source and Hermes tree: CLOSED

- `git archive 99e18c44f1c09a894125299f5469f256122244f7 tests lifeos_hook_bridge optional | sha256sum` gives `5b5b3610...` with Git 2.56.0. This equals `source_tar_sha256`. The cache `boundary-source.tar` has the same digest.
- The source map has 787 entries. It is equal, entry for entry (sha256 and executable bit), to the regular files of `git ls-tree -r 99e18c44` over the three paths. Its canonical JSON digest is `e0f11017...`, as recorded.
- Map against the `70fa8390` tree: one difference, `tests/test_memory_owner_job_processes.py`. `git diff --stat 99e18c44 70fa8390` outside `docs/` and `notes/` changes only that file, so the "test-only repair" wording at `PROVENANCE.md:23` holds.
- Import closure of the two boundary modules at `99e18c44`: `test_profile_services`, `optional.lifeos_release_manager.{removal_consumers,removal_preparation,release_programs}`, and `lifeos_hook_bridge.profile_services`. All are in the map and equal `70fa8390`. No file under `tests/`, `lifeos_hook_bridge/`, or `optional/` mentions `test_memory_owner_job_processes`.
- The six hashes in `primary-boundary.json` equal the corresponding map entries.
- The operator hashes to `fcbf0e4b...`, and the cache `account_boundary.py` has the same digest. It uses account `lifeos-073-test`, extracts `boundary-source.tar`, and copies Hermes from `packages/0.7.3-99e18c44/hermes` (line 49). Its argv equals the `command` in `primary-boundary.json`. Its PASS rule (line 93) requires exit 0, `Ran 8 tests`, a final `OK`, no `skipped=`, and unchanged source bytes.
- The raw output hashes to `f7296c0f...`, and the cache `primary-boundary.stderr` has the same digest. It lists the 8 cases, `Ran 8 tests`, `OK`, with no skips and no warnings.
- Hermes: the cache `0.7.3-99e18c44.tgz` hashes to `76b6d2fd...` and `0.7.3-70fa8390.tgz` hashes to `2deae5dc...` (the qualified archive). I applied the reconstruction rule at `QUALIFICATION-PROVENANCE.json:124` to the qualified archive, to the 99e18c44 archive, and to the extracted `packages/0.7.3-99e18c44/hermes` directory that the operator copies. All three give 18270 files and digest `803aae81...`, which equals `hermes_program_map_sha256`. The rule is complete enough to reproduce the digest without extra information.
- Round 1 inferred a 0.7.2 Hermes tree from the cleanup-era operator. That inference was wrong for this replay. `PROVENANCE.md:27` states the correction plainly.

## F4. Case naming and categories: CLOSED

- Log lines 1136, 1145, and 1164 give ERROR for the backup socket case, ERROR for the consumers case, and FAIL for the coordinator case. `QUALIFICATION-PROVENANCE.json:21-40` and the `PROVENANCE.md:7-11` table agree.
- Causes agree with the log: line 1151 `PermissionError ... /proc/814420/exe`, and line 1170 `refused_process: 'sshd-session'`.
- `RELEASE-CERTIFICATE.json:45` still says "two named workstation failures". The receipt (`:41`) and `PROVENANCE.md:13` quote it exactly and clarify it as one error and one failure, with the socket error as the third result. The certificate stays unchanged, as required.

## CONTRIBUTING.md

Line 75 adds one sentence: "Bind raw test logs, replay commands and environments, and complete replay source hashes in the qualification evidence." This covers F1 to F3 for future releases.

## Observations (no change needed)

- O1. The socket replay argv omits `-W error::ResourceWarning`, which the full run uses. Neither replay output contains a warning. With no `-W` option, unittest shows warnings by default, so no ResourceWarning happened. The receipt records the exact argv, so the difference is visible.
- O2. The socket receipts record argv, working directory, and TMPDIR, but not the full environment (for example the search path that finds `tests/`). The full-run record uses the same convention. `PROVENANCE.md:17` does not claim more than it records.
- O3. The tar digest can change with the Git version that runs `git archive`. The 787-entry source map binds each file independently of the tar format, so the binding does not depend on Git 2.56.0.
- O4. Round 1 note N1 (the "non-dumpable" wording at certificate line 45 is inherited) still applies. The supplement gives the measured causes per case, which is sufficient.

## Text checks

No em dash and no trailing whitespace in `QUALIFICATION-PROVENANCE.json`, `qualification/PROVENANCE.md`, or `CONTRIBUTING.md`. The receipt is valid JSON.

## Limits

- I did not rerun any suite and did not contact GitHub. The receipt is not published yet, so I compared it with the cache copy only.
- The cache files that I hashed are the current local state. They agree with every committed digest.
- Raw data: `data.json` in this directory.
