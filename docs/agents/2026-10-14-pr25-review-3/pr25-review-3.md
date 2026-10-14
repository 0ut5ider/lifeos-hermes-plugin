# PR25 independent review, round 3

Date: 2026-10-14

Role: Independent correctness, security, and regression reviewer

Question: Does the complete PR25 contain actionable defects after both follow-up owner denial fixes?

Model: gpt-6.1-sol, high reasoning effort

Reviewed base: c24dd7298932694d3d63a8fa3ee10f38ebd5054a

Reviewed head: cb67820f864cf6d7bd4b4190a2887eacd1c031de

## Result

No additional actionable defect is found in the reviewed changes. The current fixes pass the independent checks listed below. This review does not qualify a production release.

## Actual compiled browser checks

The browser uses the current 175-file compiled export, the real native Bun listener, the real authenticated owner dashboard, and one disposable local synthetic profile. Request instrumentation records actual fetch statuses and timestamps. For selected races, it delays delivery of actual overview responses by 12 seconds. It does not replace response content or status.

1. A revoked owner clicks Save. The actual PUT returns 403. The active browser then has zero owner rows, zero textareas, and the unavailable state while its subsequent overview response remains delayed. The primary independently confirms the DOM and a same-session GET denial. See `save403-delayed-overview.json`.
2. The owner binding is restored, and the source changes on disk. The next real overview timer returns 200. The subsequent file GET returns 200. The active textarea contains the changed current source. It does not contain the earlier body or unsaved draft. See `fresh-owner-recovery.json`.
3. An external edit changes the source after its browser review. Save returns 409. The browser retains all 24 rows and its unsaved draft. The later source remains on disk. The primary independently confirms the DOM and current source response. See `conflict-keeps-draft.json`.
4. Actual browser logout clears the cookie. Save returns 401. The browser hides all rows and textareas while the overview response remains delayed. See `save401.json`.
5. A current file read returns 403 for the revoked owner. The browser hides the complete owner surface before its delayed overview response returns. See `file-read403.json`.
6. Actual remount returns 403 for the revoked owner. The browser hides the complete owner surface before its delayed overview response returns. See `remount403.json`.
7. A real 60-second overview timer receives 200 while the owner remains authorized. The instrumentation holds that response for 12 seconds. The owner binding is then removed and Save returns 403 during the hold. After the older 200 and newer 403 have both returned, the browser still has zero rows and zero textareas. The unavailable state remains. See `late-overview-before-denial.json` and `late-overview-after-denial.json`. These observations verify the final withheld state after response reordering. They do not record every intervening animation frame.

The current real 60-second overview timer also returns 403 while an admitted file remains open. The resulting DOM contains zero owner rows, zero textareas, and the unavailable state. No timer acceleration, manual refetch, or substituted response runs. See `timer-before.json` and `timer-after.json`.

## Other independent verification

- All 29 editor backend tests pass in 47.150 seconds with ResourceWarning treated as an error. The test process uses the qualified Bun and frozen Python environment. The retained `backend.done` is 0. This set includes actual HTTP status and callback checks for 200, 401, 403, 409, and 503.
- Strict dashboard TypeScript checking passes. Both type output files are empty.
- The fresh ordered patch replay and prepared compiled export match exactly for all 175 files. Both canonical and packaged patch pairs match. See `compiled-replay.json`.
- All nine actual restore-admission statement cases pass with synthetic local inputs. The guard test runs no guest or backup mutation. See `restore-guards.json`.
- Python compilation of the core editor modules and checkpoint operators passes.
- The runtime diff, changed-file inventory, fixed registry, physical path boundaries, sealed files, current owner policy, review references, private backups, idempotency, source containment, retirement admission, interrupted recovery, shared and exclusive program locks, HTTP bounds, native snapshots, remount route, restore operators, evidence scope, and public documentation receive review.

## Limits and retained operator errors

The guard-log denial path receives source inspection and the real HTTP callback test. This round does not force a guard-log denial through the compiled browser. Its 120-second browser timer is not a separately verified case here.

The first preview open rejects `about:blank` as an invalid URL. Opening a blank owned tab without that URL works. Two unsynchronized extra file probes run before the expected rows exist. A further probe selects a missing DA identity, so it sends no file request. The corrected existing Health file probe records the actual 403. These operator mistakes do not produce a product finding. The logout fetch reports the redirect target's 404, after the real logout response clears the cookie. The subsequent real Save 401 verifies the intended loss of authority.

This round does not repeat the full 794-test archive integration run, the 716 native tests, installed guest acceptance, or the protected backup restoration. The exact 02dcd9e3 archive remains a historical acceptance checkpoint. It does not contain the follow-up browser fixes. The current program requires a new complete package and release qualification before production promotion.

No product code is edited. No commit, push, memory or journal call, production update, scheduled-task change, or personal data access occurs. The owned browser and fixture are closed after the final observation. The fixture cleanup marker records the actual cleanup result.
