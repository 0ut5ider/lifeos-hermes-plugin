# PR25 independent review, round 1

Date: 2026-10-14

Role: Independent correctness, security, and regression reviewer

Question: Does the complete PR25 diff contain actionable defects after the earlier focused editor reviews?

Model: gpt-6.1-sol, high reasoning effort

Reviewed base: c24dd7298932694d3d63a8fa3ee10f38ebd5054a

Reviewed head: c696be0435f4b5b88467635c6184e00296de3b02

## Result

One high-priority finding remains. The backend refuses revoked accounts correctly, but the compiled dashboard continues to display an already-open owner file after its automatic overview request returns 403.

I reviewed the complete changed-file inventory. I inspected the runtime changes, native source changes, compiled export handling, tests, one-time restore operators, and evidence claims. I found no second measured actionable defect in this round. This result does not certify production qualification.

## P1: Clear the active file view when the overview rejects current owner authority

Repository location: `patches/lifeos-memory-access.patch:14645-14670`, including the equivalent packaged patch. The affected native component is `LifeOS/install/LIFEOS/PULSE/Observability/src/components/HermesFiles.tsx`, particularly the per-file query and effect at lines 225-246, and the parent overview query and render checks at lines 413-430.

The file effect clears a draft only when the file query fails, the row closes, or its metadata says that reading is forbidden. An open file query has no polling interval and disables window-focus refetch. The parent overview polls every 60 seconds. It ignores the overview error state and renders retained React Query data. When the overview returns 403 after owner revocation, the component keeps the old row metadata and the open textarea.

I measured this against the actual rebuilt compiled dashboard, with real synthetic native and authenticated dashboard listeners:

1. Log in as the synthetic owner and open the Hermes tab.
2. Open `PRINCIPAL_IDENTITY.md`. The actual file GET returns 200. The textarea displays `SyntheticCoreEditorIdentity` and the synthetic owner content.
3. Remove `dashboard:basic:synthetic-owner` from the fixture configuration through `MemoryConfiguration.update`.
4. Leave the file row open. Wait for the actual 60-second overview timer without invalidating the file query.
5. The automatic overview GET returns 403 at browser timestamp 1792009704118. Its retry also returns 403.
6. The textarea still contains the complete previously admitted synthetic identity. The page does not show the unavailable state.
7. A separate explicit GET to the same file with the same browser session returns 403. This confirms that the backend currently refuses the account.

The consequence is continued owner content display after the application receives a current owner denial. The earlier close-and-reopen test does not cover this active-view path. This is a browser display admission failure. I did not observe unauthorized new backend reads or successful writes after revocation.

The parent must withhold the governed file surface on a current overview admission error and clear the active draft and review state. A fix must also cover retained guard analysis and other owner metadata in this surface. The next review should keep a file open across the real overview timer and inspect the actual compiled browser after the server denies the account. Rebuild and replay the compiled export after changing the native component.

Evidence: `active-view-revocation.json`, `settled-revocation.json`, and `browser-fixture/browser-endpoint.json`. The request instrumentation records actual fetch responses and does not replace them.

## Independent checks

- Strict dashboard TypeScript checking passes with qualified Bun 1.4.3. Both `types.stdout` and `types.stderr` are empty.
- The nine synthetic restore-admission cases pass. `restore-guards.json` records the actual admission statement results. No guest or backup command runs in this check.
- The actual compiled browser reproduces the high-priority finding above.
- Static review covers the fixed 24-file registry, owner and policy rechecks, private and retired-content admission, source references, backup publication, idempotent operations, cross-route recovery, installation and program locks, HTTP and RPC size handling, fixed remount routes, and the copied patch pairs.
- The release evidence explicitly preserves the initial 794-test setup failures and the corrected 36-test rerun. It distinguishes the staged candidate from production qualification and distinguishes synthetic Atlas cases created after restore from archive-contained cases.

## Limits and work isolation

I did not rerun the full 794-test integration set, the 716 native tests, or installed guest acceptance. The primary independently reruns the 28 focused editor tests during this review. Those tests do not exercise the remaining compiled active-view denial path.

I did not edit product code, commit, push, call memory or journal tools, or access or modify a production store. I used an isolated local synthetic account and opened a separate incognito browser tab. The fixture returns 404 for unrelated dashboard endpoints; those diagnostics are outside the core editor test surface. The primary independently confirmed the displayed synthetic identity and the same-session 403. I then closed my browser tab and stopped the fixture. Its `browser-fixture/process.done` is 0, and the runner exits 0 with no output.
