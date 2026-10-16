# Dashboard cleanup review, round 2 (coverage fixes)

- Date: 2026-10-16
- Role: independent reviewer (single agent, read-only on product and tests, no delegation, no memory or journal calls)
- Model: Claude Opus 5.5 (`claude-opus-5-5`), running in Claude Code
- Question: Does fix commit `6f22820a` resolve the three Low coverage findings (F1 to F3) of the first review with meaningful assertions, and is anything still missing?
- Reviewed commits: `6f22820a43ccb2978218dbbe28b430e93b2246bd` (fix), on top of `6232ed74296692fd1a3478510d05aad37bf5df3b` (cleanup) and `153b37c6` (pre-fix tests). Baseline bundles: `728cd17a94607ec4c119419c052060582a8b75af`.
- First review: `docs/agents/2026-10-16-dashboard-cleanup-review/dashboard-cleanup-review.md`
- Raw evidence: `data.txt` (sections 1 to 8), `tap-*.txt` (full TAP output), scripts `mutate.py` (byte copy of the first review's script), `mutate_extra.py`, `failure_messages.py`.

## Verdict

CLEAR, with the limits below. F1, F2, and F3 are resolved. Each previously surviving mutation now fails a direct assertion in the new or strengthened test, and the same mutations still survive the pre-fix tests, so the new assertions cause the detection. The new tests also pass on the pre-cleanup `728cd17a` bundles, so they describe preserved behavior and do not pin a cleanup artifact. I found no new defect in the product code or the fix commit.

## Input binding (sha256, first 16 hex; `data.txt` section 1)

| File | `728cd17a` | `6232ed74` / `153b37c6` | `6f22820a` | Checkout and HEAD blob |
| --- | --- | --- | --- | --- |
| bridge `dist/index.js` | `99676c063c685b5a` | `6848d48f1e532459` | `6848d48f1e532459` | `6848d48f1e532459` |
| release `dist/index.js` | `1aa14dbf95c80732` | `df0315bf43607657` | `df0315bf43607657` | `df0315bf43607657` |
| `tests/support/dashboard_sdk.cjs` | absent | `4cc21440b9abe73c` | `4cc21440b9abe73c` | `4cc21440b9abe73c` |
| `tests/test_dashboard_ui.cjs` | `96eebca87e37d325` | `994ed5ec51445175` | `e93778a6c1e1626f` | `e93778a6c1e1626f` |
| `tests/test_fresh_store_ui.cjs` | `6c2793b332627b12` | `38c21cd6dc854b44` | `2db1b8cd615d30df` | `2db1b8cd615d30df` |
| `tests/test_memory_dashboard_ui.cjs` | `652c0887f0609a24` | `2be7bbc41f6d3c91` | `60e653010060e369` | `60e653010060e369` |

- `6232ed74..6f22820a` changes only the three test files above (59 insertions, 5 deletions). `git diff --check` is clean.
- The other six `.cjs` files are identical at `6232ed74`, `6f22820a`, and the checkout.
- HEAD moved during the review (`b7168284`, `1a959a28`, `a4c93955`) because of the parallel Python cleanup. `6f22820a..a4c93955` changes no bundle and no `.cjs` file. It removes one line from `optional/lifeos_release_manager/dashboard/plugin_api.py`, which is Python and outside this scope.
- The checkout has no tracked or staged changes in the dashboard or test paths.

## Resolution per finding

### F1 (install refresh failure and stale status clear): resolved

New test `tests/test_dashboard_ui.cjs:470` runs the three refreshing actions (`/installation/apply`, `/installation/finalize`, `/installation/mount/recover`, handlers at `lifeos_hook_bridge/dashboard/dist/index.js:995-1021`). For each, it:

1. Makes the first POST fail, and asserts the "Could not ...: synthetic prior refusal" status.
2. Clicks again and synchronously asserts that the status is empty. This pins `setInstallationStatus("")` at `index.js:979`.
3. Lets the POST succeed with a deferred `GET /installation`, then asserts that every button in the section is disabled.
4. Rejects the refresh and asserts the failure prefix plus "synthetic refresh refusal" and an enabled button.

The `try/finally` rejects the deferred refresh even when an assertion fails, so a failure cannot hang the run. The `submitted` flag in `installationPage` routes only post-click `GET /installation` calls to the deferred promise. For `finalize`, `Promise.all` still rejects through that GET.

Evidence (`data.txt` sections 3 to 6):
- `installation-status-clear-removed` fails at step 2 (actual `['Could not install LifeOS: synthetic prior refusal']`, expected `[]`).
- `installation-succeed-not-chained` fails first through an unhandled rejection. To check that the busy assertion itself detects the defect, I also ran a variant that swallows the stray rejection. It fails with "Install prepared LifeOS waits for its pending refresh".
- Extra probes that each fail only test 9 and pass the pre-fix suite: `apply-refresh-not-returned`, `finalize-refresh-not-returned`, `recover-refresh-not-returned`, `installation-refresh-error-swallowed`. Every one of the three refreshing actions is pinned on its own, not only the first in the loop.

### F2 (connection refresh failure and await): resolved

New test `tests/test_memory_dashboard_ui.cjs:212` makes `/memory/sharing` succeed and holds the next `GET /memory` (handler `index.js:551-557`). While the refresh is pending, it asserts that "Enable memory sharing" is disabled and the status is not "Memory sharing is enabled.". After rejection, it asserts that the status is "synthetic status refusal" and the button is enabled.

Evidence:
- `connection-refresh-not-awaited` fails at line 224 (`assert.equal(button().props.disabled,true)`, actual `false`). A variant with the stray rejection handled fails at the same assertion.
- `action-show-not-awaited` now fails 5 tests (4 before), including the new one.
- Extra probes `connection-message-before-refresh` and `connection-refresh-error-swallowed` fail only the new test and pass the pre-fix suite.

### F3 (store success notice before request completion): resolved

`tests/test_fresh_store_ui.cjs:136-141` now asserts, between `onClick()` and `await pending`, that the button exists, that it is disabled, and that the success notice is absent. Lines 154-156 add the same notice check for the `start` form. This also adopts the first review's optional suggestion (explicit `assert.ok(button)` in place of `?.props.disabled ?? true`).

Evidence:
- `change-notice-before-request` fails test 16 (the "Selection started..." notice is present, expected `null`) and passes the pre-fix suite.
- Extra probe `change-request-not-awaited` now fails 2 tests (1 before).

## Findings by severity

No Critical, High, Medium, or Low findings against the fix commit or the cleanup.

Informational (pre-existing, outside the cleanup-changed path, no action required for this cleanup):

- I1. No test checks the install status line while the post-success refresh is pending. If someone moved the "LifeOS 7.40.4 installed. ..." text ahead of its `GET /installation` in `installLifeOS`, all 57 tests would still pass (`data.txt` section 7). The callback bodies of `installLifeOS`, `finalizeLifeOS`, and `recoverLifeOSMount` are unchanged since `728cd17a` (only their wrapper changed), so this gap is the same before and after the cleanup. The F1 test could close it with one extra assertion in its `try` block (status empty while the refresh is pending). I report it so that the parent can decide. It does not block CLEAR.

## Commands and counts

All runs used `git archive` exports under this directory's `scratch/`, never the shared checkout. I removed `scratch/` afterwards because the exports included copies of `tests/*.py` that a repo-wide pytest could collect. Section 8 of `data.txt` has the commands to recreate it. Node v22.22.3, Python run with `-I`.

| Check | Export | Result |
| --- | --- | --- |
| `node --test tests/*.cjs` | `6f22820a` | 57 tests, 57 pass, 0 fail, 0 skipped, 0 todo, exit 0, no non-TAP output |
| `node --test tests/*.cjs` | `728cd17a` bundles + `6f22820a` tests | 57 tests, 57 pass, 0 fail, exit 0 |
| `node --test tests/*.cjs` (control) | `153b37c6` | 55 tests, 55 pass, exit 0 |
| `node --check` bridge bundle | `6f22820a` | exit 0 |
| `node --check` release bundle | `6f22820a` | exit 0 |
| 12 review mutations (`mutate.py`) | `6f22820a` | 12 of 12 detected, 0 skipped (anchor count 1 each) |
| 12 review mutations (`mutate.py`) | `153b37c6` | 8 detected; the 4 survivors are exactly `installation-status-clear-removed`, `installation-succeed-not-chained`, `change-notice-before-request`, `connection-refresh-not-awaited` |
| 8 extra probes (`mutate_extra.py`) | `6f22820a` | 8 of 8 detected; each mutated bundle passes `node --check` |
| 8 extra probes (`mutate_extra.py`) | `153b37c6` | 2 detected, 6 survive (the 6 F1/F2 probes) |
| Section 7 probe (success text before refresh) | `6f22820a` | survives, 57/57 (I1) |

My 12-mutation results on `6f22820a` match the parent's `primary-review-fix-mutations.txt` line for line. My first `mutate_extra.py` run skipped `finalize-refresh-not-returned` because its anchor matched twice. I lengthened the anchor and reran (section 4b). Every mutation restored the bundle to `6848d48f1e532459` (logged per run).

## Limits

- All evidence comes from the Node SDK fixture in `tests/support/dashboard_sdk.cjs`. It is not React and not a browser. Setters do not re-render, effects run during render, and the fixture cannot see React scheduling, batching, stale closures, or effect dependencies. I did not render the bundles in the Hermes host, run Playwright, or test an installed plugin. Passing these tests is unit-level contract evidence, not browser or installed-plugin acceptance.
- The F3 assertions are synchronous. The mocked store requests resolve immediately, so the test proves that the notice waits for at least the `await request()` step, not for a slow request. With the current code shape these are equivalent. A deferred-request test would prove it directly.
- Synchronous handlers (for example `showSearch`) still have one extra microtask in which results are set while `busy` is still true. The first review observed this. I did not verify the claim that React batching makes this microtask unobservable, and I do not endorse it. The intermediate state is benign, as the first review explains.
- Mutation testing uses string anchors, not a parser, and covers only the paths named here.
- Known baseline behaviors (ownership activation gap, upload refusal clearing, search versus proposal refusal handling) are outside this scope and were not retested.
- I did not run Python tests or verify server routes. I made no edits to product or test files, did not touch the git index, and did not commit.

## Primary artifact note

The original raw evidence and reproduction scripts are preserved inside `evidence.tar.gz`. Extract the archive into a disposable directory to inspect or rerun them. Prompts, raw model responses, and launcher metadata stay outside Git.
