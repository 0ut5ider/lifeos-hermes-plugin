# PR25 independent review, round 2

Date: 2026-10-14

Role: Independent correctness, security, and regression reviewer

Question: Does PR25 at d0bb5b60 contain actionable defects after the active overview denial fix?

Model: gpt-6.1-sol, high reasoning effort

Reviewed base: c24dd7298932694d3d63a8fa3ee10f38ebd5054a

Reviewed head: d0bb5b603b24150e33c9ce9513b807d1cfaeaaaf

## Result

One high-priority finding remains. The actual automatic overview denial now hides the editor correctly. A current save denial still leaves the active owner content visible until a later overview request fails.

The primary independently verifies both the repaired timer path and the remaining save denial. This review does not certify production qualification.

## P1: Withhold the active owner view when a save returns an owner denial

The affected native component is `LifeOS/install/LIFEOS/PULSE/Observability/src/components/HermesFiles.tsx`, line 262. The change is carried by `patches/lifeos-memory-access.patch` and its packaged copy.

The save mutation error handler only sets an error message. It does not clear the draft, reject the parent surface, or invalidate the overview. The file query still has successful cached data. The parent overview also retains its prior successful result until its next timer request.

I measure this with the actual compiled dashboard and real synthetic native and authenticated owner listeners:

1. Admit the synthetic dashboard owner and open `PRINCIPAL_IDENTITY.md`.
2. Change the textarea through its real input event. The Save button becomes enabled.
3. Remove the dashboard owner binding through `MemoryConfiguration.update`.
4. Click the real Save button before the next overview timer.
5. The real PUT returns 403 at browser timestamp 1792010067651.
6. At timestamp 1792010072809, the page displays `API error: 403`. It also keeps all 24 owner rows and the full textarea.

The textarea contains the previously admitted synthetic identity and the unsaved synthetic draft. The page does not show the unavailable state. The file on disk remains unchanged. The primary independently confirms the displayed body, 24 rows, the recorded save denial, and a same-session file GET that returns 403.

This is a browser display admission failure after the application receives a current owner denial. I do not observe a successful unauthorized backend write. The earlier timer fix eventually hides this surface, but the owner denial must withhold it when the mutation returns. Preserve drafts for ordinary source conflicts such as 409. A fresh successful owner overview and file read must be required before the editor can resume.

Evidence: `save-denial.json`. The request instrumentation records actual fetch responses and does not replace them. The primary retains its independent confirmation separately.

## Verified fixes and other checks

- Keep a file open across the real 60-second overview timer. The overview returns 403 at timestamp 1792009992942. The actual DOM has zero textareas, zero owner rows, and the unavailable state. `active-view-fixed.json` records this result.
- Restore the owner binding and change the synthetic source on disk. The next real overview request returns 200. A new file GET returns 200. The textarea contains the changed current source, rather than the previous cached body. `fresh-recovery.json` records this result.
- Run all 28 backend editor tests independently with ResourceWarning treated as an error. All pass in 47.661 seconds. `backend.done` is 0.
- Run strict dashboard TypeScript checking independently with qualified Bun 1.4.3. It passes. Both type output files are empty.
- Run the actual nine synthetic restore-admission statement cases independently. All pass. No guest or backup command runs.
- Compare the prepared compiled export with the fresh ordered patch replay. All 175 files match exactly. `compiled-replay.json` records the complete file map.
- Compare both canonical and packaged patch pairs. Both pairs match exactly.
- Review the complete changed-file inventory and runtime diff. Inspect the fixed registry, path and owner boundaries, current policy checks, source references, private publication and backups, interrupted recovery, installation and program locks, HTTP and RPC bounds, native diagnostic snapshots, fixed remount route, tests, restore operators, and evidence scope.

I find no additional measured actionable defect in this round. The protected checkpoint operator preserves its exact archive and isolated guest scope. The historical candidate package remains distinct from the browser fix, which still requires complete package qualification before promotion.

## Limits and isolation

I do not rerun the full 794-test integration set, the 716 native tests, the installed guest acceptance, or the protected backup restoration. The focused checks and synthetic browser probe do not replace those release gates. The browser fixture returns 404 for unrelated dashboard endpoints. Those diagnostics are outside the core editor test surface.

The first asynchronous recovery observation exceeds the preview tool's 15-second evaluation timeout while waiting for the real 60-second timer. A later actual observation records the successful overview and fresh file read. No timer or response is substituted.

I do not edit product code, commit, push, call memory or journal tools, or modify production. All file and configuration probes use a local synthetic fixture. I close my owned browser tab and stop the fixture after the primary confirmation. The fixture cleanup marker and runner outputs record the final cleanup result.
