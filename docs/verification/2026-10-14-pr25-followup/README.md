# PR25 follow-up review

Three additional independent rounds review PR25. The first two rounds find two high-priority cached-display issues. The third round clears the fixes at program commit cb67820f864cf6d7bd4b4190a2887eacd1c031de. The reports and raw measurements are retained:

- [Round one](../../agents/2026-10-14-pr25-review-1/pr25-review-1.md): an open identity remains visible after the automatic overview returns 403.
- [Round two](../../agents/2026-10-14-pr25-review-2/pr25-review-2.md): the timer fix passes, but Save 403 keeps the active draft and all 24 rows visible.
- [Round three](../../agents/2026-10-14-pr25-review-3/pr25-review-3.md): no remaining actionable findings.

The first fix withholds the complete core surface on an overview error and disables overview retries. The second fix preserves typed HTTP status and reports core owner denials to the parent before returning the error. File reads, guard analysis, Save, and remount share that behavior. Only 401 and 403 trigger this refusal. A 409 source conflict preserves the draft. A denial revision prevents an overview response started before a denial from clearing the refusal. Recovery requires a successful current overview and a fresh file read.

The primary verifies 29 editor tests in 48.974 seconds with ResourceWarning treated as an error. The new real HTTP test checks successful responses, existing API exports and headers, typed errors, and denial callbacks. It fails before the status change and passes afterward. All six patch bundle and real source-preparation tests pass in 3.249 seconds. All nine synthetic restore-admission cases pass. Strict TypeScript checking passes. The rebuilt dashboard retains two existing native warnings. Fresh ordered patch replay matches all 175 compiled files.

The third reviewer independently passes all 29 editor tests in 47.150 seconds, strict types, exact compiled replay, patch-copy equality, and the nine restore guards. The actual compiled browser verifies immediate Save 401 and 403 refusal, file-read and remount 403 refusal, fresh owner recovery, a preserved draft and later disk edit after 409, the real 60-second overview denial, and the final withheld state after an older successful response arrives after a denial. Selected actual overview responses are delayed by 12 seconds; their content and status remain unchanged. The primary independently confirms the repaired save denial and conflict behavior. The primary also confirms the repaired overview denial during round two.

The guard-log denial path has source inspection and real HTTP callback coverage. This review does not separately force that denial through the compiled browser. The late-response check records the resulting state, not every animation frame. The optional final primary timer read reaches an already closed reviewer tab. Its tool error remains in final-timer-tool-receipt.json. The final timer result is the reviewer's actual timer-after.json, not that optional tool receipt.

All three synthetic browser fixtures exit cleanly. Their profiles and owned tabs are removed. No production service, scheduled task, or personal store changes during this review.

The 02dcd9e3 candidate archive remains its immutable historical checkpoint. It does not contain these fixes. Complete package qualification must run again before release. The default development and daily profiles remain on 0.4.3. The separate Thursday automatic morning observation remains unchanged.
