# Independent restore closure review

Date: 2026-10-02.

Agent role: independent correction reviewer, Cerebo. Review only.

Question: Do commit 1333713's corrections close R1 through R3 from the preceding Sol review while preserving the original F1 through F4 corrections?

Assigned model: GPT-6.1-Sol. Assigned reasoning effort: high. This agent performs the review directly. No subagent or other agent CLI runs.

Reviewed head: `13337135d79245fc79eca427e595446a7ae96c76`.

Compared correction baseline: `f6620c5616686c583e6755d7557df8f9d747c200`.

PR context: LifeOS Hermes plugin PR #1. This report uses local Git and the supplied reports. No GitHub request or other remote network request runs.

Adrian, R1 through R3 close within the tested correction scope. The actual filesystem and process death probes preserve the retained targets and recover the prior installation. The original F1 through F4 corrections remain closed within their previously bounded scope. One newly reproduced inherited caller defect remains: recovery accepts requests that the corresponding restore route refuses because recovery omits the shared request admission guard. This report does not certify the complete hook or memory release.

## Correction closure

| Finding | Result | Evidence |
| --- | --- | --- |
| R1: Profile or baseline archives cross filesystems and fail after program swap | Closed in tested layouts | The archive payload moves into a private directory beside each target. Real `/tmp` and `/dev/shm` probes cover profile only, baseline only, and both on the alternate filesystem. Source tests cover successful restore, verification rollback, and interrupted recovery with profile and baseline on the alternate filesystem. No EXDEV failure occurs. |
| R2: Late profile guard refuses after program swap and never restarts | Closed for the reproduced regular-file edit | The equality checks precede the program swap. A late edit injected immediately after the selected program moves is archived, the prior profile returns, and stop/start/verify complete. The three filesystem layout probes all record `['stop', 'start', 'verify']`. |
| R3: Failed restore becomes `failed`, so authenticated recovery refuses | Closed | The real worker exception handler maps `stopped`, `swapped`, `restoring`, and `rollback_failed` to `interrupted`. All four states reach authenticated local recovery with a fresh action-bound owner grant. An `applied` transaction remains `applied` after harmless refusal and reaches restore again. |
| F1: Later Hermes profile edits disappear on version restore | Closed within the bounded regular-file profile scope | Existing edits, modes, deletion, plugin/tree changes, missing metadata, post-stop refusal, late edit retention, and archive publication tests pass. Process death and repeated recovery preserve previously retained archive payloads. |
| F2: Direct child admission checks only its model | Remains closed in the reviewed direct gateway path | The file is unchanged relative to f6620c5. Both actual local child request tests pass, including forgotten system and generated user claims, approved route, invalidated history, changed ownership, and removed configuration. This is not all native inference route acceptance. |
| F3: Development recorder retains unknown environment values | Remains closed for supported mappings | The file is unchanged. All 32 recorder tests pass. Seven repeated boundary probes scrub synthetic unknown values and their echoes across mapping names, case, outer JSON, aliases, subsequent artifacts, and JSON bytes. |
| F4: Mount preparation retains obsolete credential copies | Remains closed within reviewed lifecycle | The file is unchanged. Mount transaction tests pass. Thirteen repeated probes validate terminal removal, pending retention, orphan cleanup, binding/identity refusal, malformed journals, missing snapshots, and symlink handling. |

## Reproduced finding

### N1. Medium: The recovery route omits the fixed request admission guard

Classification: newly reproduced inherited caller defect. The executable correction does not introduce this omission. The recovery route is identical at f6620c5 and 1333713; `raw/inherited-recovery-route.txt` records the earlier definition.

Exact locations: `lifeos_hook_bridge/dashboard/plugin_api.py:595` defines a recovery endpoint with no Request argument or call to `_fixed_mount_request`. That helper at line 164 refuses a foreign Origin, any query parameters, and any body. The restore endpoint at line 606 calls it. `_resume_lifeos_update` at line 614 then issues authorization, publishes the modified request/status, and reaches launch.

Caller path: authenticated owner session -> POST `/installation/update/recover` -> `_memory_account` -> recoverable job selection -> `_resume_lifeos_update` -> grant publication and worker launch.

Expected behavior: recovery enforces the same installed dashboard Origin and empty fixed request contract as restore and other protected mount operations. A foreign Origin returns 403. A query or body returns 400. These refusals occur before grant issuance and launch.

Observed behavior: three separate disposable, authenticated fixtures receive HTTP 200 for (1) `Origin: https://other.invalid`, (2) `?job=other`, and (3) a JSON body containing fabricated account/job values. Each request issues a new authorization, changes job status, and reaches captured launch. The authorization still names the real authenticated owner and the actual selected job. No identity or job substitution is established.

Evidence: `raw/probe_recovery_admission.py`, `raw/probe-recovery-admission.txt`, and `raw/probe-recovery-admission.exit`. The three records show HTTP 200, one launch call, authorization issued, and status changed. Real Hermes password sessions and the real local ASGI routes handle admission and grants. Only service launch is captured. These are caller boundary probes, not a running service or browser acceptance test.

The initial negative assertion probe also fails at the captured launch for the foreign Origin request. Its complete traceback and original script remain in `raw/caller-origin-initial.txt` and `.py`. The subsequent direct probe establishes the HTTP and state effects without conflating a probe assertion with a production exception.

Recommended correction: make recovery accept Request and call `_fixed_mount_request` before job selection and authorization. Add authenticated origin/query/body refusals and confirm that they leave job bytes, grants, and launch count unchanged. The primary agent has this evidence and has stated that it will correct the omission.

Security limit: this review does not establish browser cross-site cookie transmission, a CSRF exploit, or arbitrary owner impersonation. Those claims need browser and cookie-policy evidence. The definite result is the missing request contract at an endpoint that starts recovery work.

## Filesystem and process death evidence

`raw/probe_restore_closure.py` produces nine scenario records. Three cover successful late-edit retention with the profile, baseline, or both on the alternate filesystem. The observed device IDs are 52 for `/tmp` and 27 for `/dev/shm`. The retained payload and its original target share a device. Every existing retained payload parent is mode 0700. The restored synthetic environment file retains mode 0600.

Five scenarios terminate a child process with real SIGKILL immediately after an actual rename boundary: archive index publication, config retention, plugin-directory retention, baseline retention, and baseline publication. Each child exits -9 with empty stdout/stderr. The transaction remains `restoring`. Recovery produces `rolled_back`, owned-v1 program content, prior configuration, prior baseline bytes, and preserved environment/plugin data. Previously created retained payloads remain at their recorded locations with their contents intact.

The ninth scenario kills restore after config retention, kills recovery after baseline retention, and kills recovery again after config retention. A fourth attempt completes. Four independent archive indexes remain, and the first selected configuration archive still contains `selected config`. No destructive fallback or cross-filesystem copy-and-delete move runs.

The index publication probe terminates before the payload rename. Its index names a planned destination that does not exist. Recovery succeeds and retains the still-live target in another archive. The index therefore records intent as well as completed retention. Operators must inspect path existence when reading an interrupted index.

The syscall instrumentation runs inside the child and invokes the real rename before SIGKILL. It isolates the specified boundary and uses real local files. It does not establish all filesystem fault behavior or live gateway service behavior. Stop/start/verify callbacks record requested lifecycle actions.

## Verification

| Selection | Result | Raw evidence |
| --- | --- | --- |
| Update transaction, worker, authenticated dashboard, mount transaction, direct children | 55 pass in 44.327 seconds; exit 0 | `raw/focused-tests.txt`, `raw/focused-tests.exit` |
| Development recorder tests | 32 pass in 6.832 seconds; exit 0 | `raw/recorder-tests.txt`, `raw/recorder-tests.exit` |
| Filesystem and process death probe | Nine scenarios pass; eight SIGKILL exits; exit 0 | `raw/probe-restore.txt`, `raw/probe-restore.exit` |
| Worker/caller mapping probe | Five scenarios pass; exit 0 | `raw/probe-callers.txt`, `raw/probe-callers.exit` |
| Mount cleanup boundary probes | Thirteen complete expected-behavior records | `raw/probe-cleanup.txt` |
| Recorder boundary probes | Seven complete expected-behavior records | `raw/probe-recorder.txt` |
| Recovery request admission probe | Three deliberate defect reproductions; assertions confirm observed behavior; exit 0 | `raw/probe-recovery-admission.txt`, `raw/probe-recovery-admission.exit` |
| Initial negative caller probe | Exit 1 at the foreign-Origin reached-launch assertion; retained as finding evidence | `raw/caller-origin-initial.txt`, `raw/caller-origin-initial.py` |

Repository test total: 87 pass, zero failures, zero skips, zero warnings. Additional scenario total: 37, comprising 34 expected-behavior scenarios and three deliberate inherited defect reproductions. Counts do not include earlier reports or the concurrent primary gate. A probe's zero exit confirms its assertions, including assertions about observed defective behavior.

The prepared LifeOS source, Hermes source, native TaskGovernance path, repository/tests Python path, and disabled bytecode setting match the supplied environment. `raw/commands.sh` records replay commands. The test interpreter is `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. The initial negative caller failure is not the primary agent's earlier missing-source fixture failure; this reviewer always exports the supplied native fixture environment.

`raw/reviewed.diff`, source copies, head record, source hashes, and the empty `raw/unchanged-f2-f4.diff` preserve the pinned reviewed implementation. The previous Sol and Opus reports are inputs, not newly executed evidence.

## Static observations and acceptance limits

The new index path is published before each target rename. The implementation syncs the index file, archive directory, archive root, source parent, and retained target parent. This and the process death probes substantiate recovery after process exit.

Power-loss durability remains outside the tested scope. Static inspection shows that creation of `mount-before-restore` does not explicitly sync its parent snapshot directory. The transaction manifest and program directory swaps also retain the earlier durability limits. This is an inherited durability hypothesis, with a remaining parent-directory sync detail visible in the new implementation. No power-loss archive loss is reproduced and no such defect is claimed here. A SIGKILL is not power loss; `/dev/shm` is intentionally volatile.

Concurrent detached restore/recover launches and hostile same-account path substitution remain inherited hypotheses or documented boundary limits. This review does not promote them to reproduced findings. It does not run two workers concurrently.

The review does not certify complete hook parity, complete memory acceptance, real model providers, real systemd lifecycle, browser cookie/Origin behavior, ownership activation, remote capture, SSH, Docker, full source preparation, power loss, or the complete release gate. All source tests and probes use disposable synthetic data. The local test gateway used by the child tests is disposable; no deployed server configuration or remote system changes.

Only this report directory contains reviewer-authored artifacts. No source or repository test edits, settings, services, commits, pushes, memory/journal calls, or activation occur. The primary is notified when source reads and tests finish so its next correction can begin safely.

## Review recommendation

Accept R1 through R3 as closed for the reviewed correction scope. Preserve the F1 through F4 corrections. Correct N1 and verify its refusal behavior before treating these immediate recovery callers as closed. Keep the broader release decision with the primary gate and Adrian.

Adrian's review should focus on the retained targets living outside the version snapshot, planned index entries after interruption, the chosen late-edit policy of retaining the edited version in an archive while restoring the prior live profile, and the common Origin/request contract for recovery. Process death acceptance has concrete evidence; power-loss and live-service acceptance do not. No changes outside the disposable fixtures and report directory need to be undone.
