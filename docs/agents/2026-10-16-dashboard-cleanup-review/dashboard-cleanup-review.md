# Dashboard cleanup review

- Date: 2026-10-16
- Role: independent reviewer (single agent, read-only on product and tests, no delegation)
- Model: Claude Opus 5.5 (`claude-opus-5-5`), running in Claude Code
- Question: Does the bounded dashboard cleanup keep UI text, request shapes, authorization, recovery, saved formats, and user behavior unchanged, and do the new and converted Node tests pin the changed paths faithfully?
- Reviewed range: `728cd17a94607ec4c119419c052060582a8b75af..6232ed74296692fd1a3478510d05aad37bf5df3b` (commits `b93b92b3`, `d6e5407a`, `8e4ca566`, `6232ed74`)
- Checkout HEAD during the review was `153b37c6` (parent's later docs commit). The dashboard bundles and `tests/` in the checkout are byte-identical to `6232ed74` (`data.txt` section 2), so the test runs below exercise the reviewed code.
- Raw evidence: `data.txt` in this directory (full diff, test output, mutation and probe output). Helper scripts: `mutate.py`, `probe.cjs`.

## Verdict

No correctness defect and no hidden behavior change found in the reviewed range. Every `MemoryPreferences.action` caller passes the handler that matches its old dispatch branch, every asynchronous handler is awaited, and the busy, failure, and refresh flows produce the same observable states as the original code on every path I probed, including paths the suite does not cover.

Not CLEAR in the strict sense: three Low test-coverage findings remain (F1 to F3). They do not block integration. They mean the suite would not catch a future regression in those specific paths, and they contradict one implementer claim ("every changed bundle path got a test").

## Checks run

| Check | Result |
| --- | --- |
| `node --test tests/*.cjs` at checkout | 55 tests, 55 pass, 0 fail, exit 0 |
| `node --check` bridge bundle | OK |
| `node --check` release bundle | OK |
| `git diff --check 728cd17a 6232ed74` | clean |
| Suite at `728cd17a` (isolated `git archive` export) | 42 tests, 42 pass |
| Suite at `8e4ca566` (new tests, unchanged bundles; bundle diff against `728cd17a` is empty) | 55 tests, 55 pass |
| Tests changed in `8e4ca566..6232ed74` | none |
| String-literal set comparison, both bundles | no literal added or removed (701/701 bridge, 166/166 release) |
| Style sheets and manifests in range | unchanged |
| Python routes for every touched request path | present in `lifeos_hook_bridge/dashboard/plugin_api.py` (`data.txt` section 17) |

The implementer's test and syntax claims reproduce. I did not rerun their 19 mutations. I ran 12 of my own on an isolated export (below).

## Findings

### F1 (Low, test coverage): the install-action refresh failure and status clear are not pinned

- Location: `lifeos_hook_bridge/dashboard/dist/index.js:977-983` (`runInstallationAction`); tests at `tests/test_dashboard_ui.cjs:439` and `:456`.
- Cause: the success test resolves every follow-up GET, and the failure test rejects only the POST. No test makes the POST succeed and the follow-up refresh fail. No test observes the status line while a request is pending.
- Concrete scenario: a later edit changes `.then(succeed)` to `.then(function (result) { succeed(result); })`. Then **Install prepared LifeOS**, **Finish LifeOS setup**, and **Restore interrupted mount** release the busy state before their refresh finishes, and a refresh failure becomes an unhandled rejection instead of "Could not install LifeOS: ...". My mutation `installation-succeed-not-chained` makes exactly this change and the suite still passes 55/55. The mutation `installation-status-clear-removed` (stale status text stays visible during a new action) also survives.
- Current code is correct: the differential probe shows identical old and new states for all three actions (busy held while the refresh is pending, then "Could not ...: synthetic refresh refusal" and busy released; `data.txt` section 13).
- Corrective action: add one test case per refreshing action (`/installation/apply`, `/installation/finalize`, `/installation/mount/recover`) with POST success and a deferred follow-up GET. Assert all section buttons stay disabled while the GET is pending, then assert the failure prefix plus reason and enabled buttons after rejection. Add an assertion that a previous status line is empty while the next action is pending.
- Verification: both surviving mutations above must fail the new test.

### F2 (Low, test coverage): a failed status refresh after a connection change is not pinned

- Location: `lifeos_hook_bridge/dashboard/dist/index.js:551` (`showConnectionChange`); test at `tests/test_memory_dashboard_ui.cjs:185`.
- Cause: the connection test always lets the `GET /memory` refresh succeed.
- Concrete scenario: an edit to `SDK.fetchJSON(memoryEndpoint).then(setMemory)` drops the await. The owner then sees "Memory sharing is enabled." and the controls unlock while the status refresh is still in flight, and a refresh failure no longer reaches the message line. Mutation `connection-refresh-not-awaited` survives.
- Current code is correct: probe shows the same states before and after (busy while pending, then message "synthetic status refusal" and busy released).
- Corrective action: add a case where `/memory/sharing` succeeds and the next `GET /memory` rejects. Assert the button stays disabled until the rejection and the status line then shows the refusal reason.
- Verification: mutation `connection-refresh-not-awaited` must fail.

### F3 (Low, test coverage): the order of notice and request in `FreshStores.change` is not pinned

- Location: `lifeos_hook_bridge/dashboard/dist/index.js:750-758`; tests at `tests/test_fresh_store_ui.cjs:123` and `:161`.
- Cause: both tests read the notice only after the request settles.
- Concrete scenario: moving `setNotice(done)` before `await request()` would show "Store removed. The current installation is unchanged." while the DELETE is still pending, and the final state would still match. Mutation `change-notice-before-request` survives.
- Corrective action: in the "each store change" loop, assert that the success notice is absent between `onClick()` and `await pending`.
- Verification: the mutation must fail.

## Items checked and found correct

1. **`MemoryPreferences.action` handler mapping** (`index.js:508-560`, callers at 581, 595, 614, 651, 655, 671, 701, 709, 714, 722). Old dispatch: `/adoption/preview`, `/adoption`, `/review` by `body.tool` (proposals, decide, otherwise search), `/owner`, otherwise the connection branch. Each of the 10 callers passes the matching handler. The four connection callers (`/sharing`, two `DELETE /connections/{client}`, `POST /connections`) all pass `showConnectionChange`, which is the old fallthrough branch. No caller omits the handler. Handler bodies match the old branches statement for statement. `showDecision` replaces an inline refresh request with `postJSON`, which builds the same init object. Swap mutations (proposals to search, claim to connection, preview to adoption) each fail 1 to 3 tests.
2. **Awaiting.** `action` awaits `show(...)`, so the async handlers `showAdoption`, `showDecision`, and `showConnectionChange` finish their refreshes before `setBusy(false)`, and their errors reach the same `catch`. `change()` awaits `request()` and `load()`. `runInstallationAction` chains `.then(succeed)`, which adopts the promise each callback returns. The `start` and `choose` handlers lost `async` but return the promise from `change`, and `event.preventDefault()` still runs first.
3. **Request shapes.** `postJSON` yields `{ method, headers: { "Content-Type" }, body }` in the old key order. `choose` keeps its own init (no header when there is no body). `remove` keeps `{ method: "DELETE" }`. Installation actions keep `{ method: "POST" }`. `readScopes` keeps `["project", "principal"?, "assistant"?]` order. `projectNames` keeps trim and empty filtering. The SSH enrollment body keeps its key order. `encodeFile` is the same byte loop, still after the size checks.
4. **Renames.** `origin` (import begin) and `assigned` (adoption) remove shadowing and change no value. In the release bundle, `step` replaces the `name` parameter. I read the whole `action` body (`optional/.../index.js:169-186`); it has no other reference that now resolves to the `name` state.
5. **Removed assertions.** Seven removed lines contain `assert` (`data.txt` section 9). Five are `assert.ok(component...)` checks, now done by the shared `component()` helper, which asserts with its own message. `intent === "install"` became a stricter `deepEqual` of the full body. The `Operation:` check became `assert.ok(find(...))` with the same predicate. No assertion was dropped without a replacement. Assertion counts rose or held in every file except `test_memory_removal_ui` (13 to 12, the folded `assert.ok(component)`).
6. **Shared harness** (`tests/support/dashboard_sdk.cjs`). It matches the old per-file copies: one effect per mount, setters that do not re-render, children flattened one level. `preview()` and `mount()` reset hook state. Two semantics differ, and neither hides a bug in this range:
   - `test_memory_portability_ui` now runs the child component's first effect on mount. Before, the mounted parent had already used the single effect. Neither `MemoryImportReview` nor `MemoryExportReview` declares an effect (effects exist only at `index.js:353, 491, 765, 851`), so this changes nothing.
   - `test_memory_removal_ui` now mounts the real release page with `installed: true` from the mock instead of writing `states[4] = true`. This is more faithful. All its assertions select POST calls, so the added GET polls do not affect them.
   The harness cannot detect stale closures, effect dependency bugs, or React scheduling, and it runs effects during render. These limits existed in every old copy and are stated in the harness header.
7. **Timing of synchronous handlers.** The implementer's report says React batching makes the extra microtask unobservable. I did not verify React's scheduler and do not rely on that claim. My microtask-step probe shows the one real difference: for a synchronous handler such as `showSearch`, the new code has one extra microtask in which the results are set and `busy` is still true (`data.txt` section 13, `searchMicrotasks`). That intermediate state (results visible, controls disabled) is benign. The original async branches already had the same kind of intermediate state (for example, the adoption message is set before the status refresh, with `busy` still true). So even if a render did land in that microtask, the owner would see nothing new or wrong.

## Baseline issues (pre-existing, not introduced here)

1. Known ownership activation gap: **Review publication plan** appears only when `decisions` is non-empty (`index.js:199` at `6232ed74`), so an empty or no-import review cannot reach activation. Deferred by the brief.
2. A refused oversize profile file clears earlier valid file choices (pinned with a comment in the new upload test).
3. A refused search clears shown results, while a refused proposal review keeps the list. The behavior is inconsistent and both are pinned.
4. `DELETE /memory/connections/{client}` sends `Content-Type: application/json` with no body. This is harmless and unchanged.

## Optional suggestions (not defects)

- `tests/test_fresh_store_ui.cjs:139`: `?.props.disabled ?? true` passes when the button disappears. All four buttons render a `disabled` prop today, so the check is effective. An explicit `assert.ok(button)` before it would make the intent clear.
- The title of `tests/test_memory_dashboard_ui.cjs:212` says "keep the previous proposal list", but the test shows that a refusal leaves an unloaded list unloaded. The guard is still pinned (removing it would show "No pending changes."). A rename or a preloaded list would match the title.
- Three `action(..., undefined, handler)` call sites use a positional `undefined` body. This is acceptable as is.

## Unresolved objections

None against the implementation. My one disagreement with the implementer's report is the claim "every changed bundle path got a test that passed on the unchanged bundles". F1 to F3 show three changed paths without a pinning test. The same claim about the React timing being "not observable" is unverified (item 7), though immaterial.

## Coverage limits

- The Node fixture, not React or a browser. I did not render the bundles in the Hermes host, run Playwright, or exercise the real SDK `fetchJSON`.
- I checked the Python routes only for existence. Because every request shape is byte-equivalent to the baseline, the server contract is inherited, not re-verified. I ran no Python tests.
- Literal comparison and mutation anchors use regex and string matching, not a parser.
- I ran mutations and probes only on `git archive` exports under this directory's `scratch/`. I removed `scratch/` after recording the output, so `mutate.py` and `probe.cjs` need a fresh export to rerun (`git archive <commit> lifeos_hook_bridge/dashboard optional/lifeos_release_manager/dashboard tests | tar -x -C scratch/<commit>`, then copy `tests/support/dashboard_sdk.cjs` into the `728cd17a` export for `probe.cjs`).
- I did not edit product or test files, did not touch the git index, and did not commit.

## Primary artifact note

The original raw evidence and reproduction scripts are preserved inside `evidence.tar.gz`. Extract the archive into a disposable directory to inspect or rerun them. Prompts, raw model responses, and launcher metadata stay outside Git.
