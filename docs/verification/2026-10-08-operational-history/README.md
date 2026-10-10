# Operational history growth baseline

Date: 2026-10-08. The baseline uses the fixed operational-views-third candidate and its independent original native control.

The native algorithm reader folds complete work-event history. It keeps up to 200 movement points per run and then keeps the 500 most recently moved run series. It does not restrict the complete event file to one MiB or 2,048 records. A quiet active run can therefore retain a progress curve from an event before the reader's recent tail window.

Two actual authenticated HTTP cases reproduce the managed limit. A 2,051-record log contains 336,357 bytes. A 5,001-record log contains 1,320,157 bytes. Each file starts with a current quiet run's movement event. Later rows describe a different run. The independent native response retains the first run's one-point curve. The managed response returns 503 in both cases. baseline.txt retains the exact inputs' measured sizes and the two failed assertions.

The correction must preserve the native all-time fold. It must continue to exclude private and retired event records and check current source identity and authority before delivery. It must retain bounded per-record validation, private temporary processing, native response limits, and cancellation. Truncating the source to a recent tail would remove the measured quiet-run curve and would not meet this acceptance case.

No large-history implementation or passing growth result exists at the time of this baseline. The operational route boundary and asynchronous stream have separate accepted focused evidence. This growth case remains a daily-release gate.

## Streamed candidate and measured descriptor defect

The first streamed candidate removes the total work-history size and record caps. It validates bounded batches and supplies anonymous private event snapshots to the existing native fold. Algorithm activity uses the same path with its original 512-KiB byte tail. Per-record validation remains bounded at 256 KiB and the individual validation transport at three MiB. The parent supplies a read-only descriptor to the child. Zero links and private permissions prevent named artifacts after process death.

All six first growth and frontend checks pass. The expanded first gate passes seven of eight cases and reproduces a torn UTF-8 defect. A separate process capture identifies the premature small-file review decode. The correction fingerprints the incomplete raw bytes and decodes only complete lines. The expanded second gate passes 38 cases. The next focused gate passes 41 cases in 72.264 seconds, including batch changes, inode replacement, revocation, invalid descriptors, line endings, exact small-source review, and actual process death.

The first combined gate runs 420 cases in 567.239 seconds and reports three intermittent failures. Its result is not accepted. Selective exception tracing captures an EBADF statx failure inside the actual native action. The initial instrumentation only sees fixture calls because the dashboard loads the implementation under a separate package namespace. Preloading that namespace changes the observed behavior. observe_boundary_failures.py keeps lazy imports intact and records the actual request exception without capturing credentials.

The primitive descriptor experiment runs 40 borrowed streams and 40 streams that open a separate reader. Borrowed stream cleanup closes the supplied descriptor immediately in nine cases and by the next event-loop turn in 30 cases. Separate reader cleanup closes the supplied descriptor in zero cases. The renderer regression fails in all 12 baseline calls after cleanup. The 40-call parent-process control passes but cannot establish child descriptor lifetime. The second candidate opens its own reader through the validated descriptor's proc entry. The accepted results for that candidate appear below.

Exact source review still uses the existing bounded full-source preview. Large older log files cannot receive full-source review through that preview. Retirement age fences continue to exclude unreviewed old rows. The streaming correction does not grant review or restore old facts. The original source files remain unchanged.

## Accepted second candidate

The second candidate passes all 43 focused history, operational reader, asynchronous relay, and frontend checks in 79.626 seconds. The actual renderer preserves the supplied descriptor in all 12 regression calls. The corrected combined gate passes all 422 tests in 575.240 seconds with warnings treated as errors and no skips. final-adjacent-gate.txt and its completion status retain the complete result. run_final_gate.sh records the fixed source selection and unchanged independent control trees.

The dashboard build passes. It retains the existing workspace-root and ambiguous CSS utility warnings. The separate strict TypeScript check passes in the focused and combined gates. final-dashboard-build.txt retains the build output. source-identity.json binds both native programs and both identical patch copies to the prepared operational-history-second tree. caller-source-changes.json compares all 330 inventory program hashes with the overview candidate and identifies only Observability and MemoryAccess changes.

The growth correction preserves the complete native work-event fold and the original bounded activity tail. It removes the total history size and record caps while keeping bounded individual records and validation batches. The current growth gate measures a 0.887853-second response and a 0.517778-second live update on disposable localhost services. These results do not establish installed-server throughput. No running installation activates ownership, and remaining native reader and writer coverage and daily acceptance stay open.
