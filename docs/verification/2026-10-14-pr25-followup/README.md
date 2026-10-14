# PR25 follow-up review

The full independent review of head c696be04 identifies one high-priority browser issue. After the automatic overview returns 403 for a revoked owner, an open file keeps displaying its cached body. The primary independently confirms the actual textarea and a same-session file refusal. The raw failing result is active-view-before.json. The reviewer report is [pr25-review-1.md](../../agents/2026-10-14-pr25-review-1/pr25-review-1.md).

The fix makes an overview error withhold the complete governed core-file surface. The overview does not retry a refused request. Unmounting the file rows discards their active drafts and reviewed references. A temporary overview error also hides the editor. Access resumes only after a successful current overview and a fresh file read.

The 28 backend editor tests pass in 46.796 seconds with ResourceWarning treated as an error. All nine synthetic restore-admission cases pass. Strict TypeScript checking passes. The rebuilt dashboard retains the two previously recorded native warnings. A fresh ordered replay of all patches matches all 175 compiled files. The post-fix compiled-browser check and independent repeat review are pending.

The 02dcd9e3 candidate archive remains an immutable historical checkpoint. It does not contain this fix. Complete package qualification must run again before release. The default development and daily profiles remain on 0.4.3. The separate Thursday automatic morning observation remains unchanged.
