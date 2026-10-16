# Dashboard and component-test cleanup

- Date: 2026-10-16
- Agent role: implementation agent for the dashboard cleanup task (single agent, no delegation)
- Model: Claude Opus 5.5 (`claude-opus-5-5`), running in Claude Code
- Question: Which unused declarations, duplicated scaffolding, confusing branches, and local indirection can be removed from the two dashboard bundles and the Node component tests without changing behavior? Implement the worthwhile, bounded cleanups and verify them with focused tests.
- Worktree: `/home/outsider/.cache/lifeos-code-cleanup-20261016/dashboard-cleanup`, branch `feature/dashboard-cleanup`
- Starting commit: `728cd17a94607ec4c119419c052060582a8b75af`
- Final code commit: `fba9bce1` (the report commit follows it; `commit.txt` in this directory lists both hashes)

## Result

Both bundles keep their visible text, classes, accessibility attributes, request paths, request bodies, and approval/action sequence. The bridge bundle drops from 1398 to 1364 lines. The release bundle changes one parameter name. The eight Node test files now share one SDK fixture, `tests/support/dashboard_sdk.cjs`. The suite grows from 42 to 55 tests, and no assertion was removed. All 55 pass. Both `node --check` runs pass. `git diff --check` is clean.

## Commits

| Commit | Subject | Content |
| --- | --- | --- |
| `2d03102f` | test(dashboard): share component SDK harness | Moves duplicated SDK, hook, loader, and search scaffolding into one helper. Bundles unchanged. |
| `1ab50722` | test(dashboard): characterize action outcomes | 11 characterization tests and 2 strengthened assertions, all passing against the unchanged bundles. |
| `3ba2ed63` | test(dashboard): characterize fresh store changes | 2 characterization tests for the FreshStores handlers, passing against the unchanged bundles. |
| `fba9bce1` | refactor(dashboard): share request and action flows | The bundle cleanup. No test edits after `3ba2ed63`. |
| `14e2e34e` | docs(agents): record dashboard cleanup review | This report, `checks.txt`, `data.diff`. |
| `8a2cd238` | chore(agents): mark raw cleanup diff as data | Directory-local `.gitattributes` for `data.diff` only. |

`git diff --check 728cd17a HEAD` failed after the report commit, and only on `data.diff`: a raw diff has a single-space context line for every blank source line. The code and test range (`728cd17a..fba9bce1`) was clean. The repository's root `.gitattributes` already gives its patch copies `whitespace=-trailing-space,-blank-at-eof`. I applied the same rule to this one file with `docs/agents/2026-10-16-dashboard-cleanup/.gitattributes` and left the root file untouched. After that, the committed range is clean. If the parent prefers no attribute file, dropping `8a2cd238` and `data.diff` from the cherry-pick restores a clean range.

## Changes

### Bridge bundle (`lifeos_hook_bridge/dashboard/dist/index.js`)

1. **`postJSON(url, body)`** builds the `{ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }` request that was spelled out 10 times. Callers: import `post`, export `post`, HTTP `post`, activation and return workflow requests, pending-proposal refresh, fresh store start, baseline preview, baseline save. The key order of the init object is unchanged. `MemoryPreferences.action` and `FreshStores.choose` keep their own init construction, because they omit the body (and, in `choose`, the header) when no body is given.
2. **`encodeFile(file)`** replaces two copies of the byte-to-base64 loop in the profile-file and portable-bundle upload handlers. The size checks stay at the call sites and still run before the file is read.
3. **`readScopes(principal, assistant)` and `projectNames(value)`** replace two copies of grant construction (HTTP `grant()` and the SSH enrollment form). Both grants still start with `["project"]` and add `principal` and then `assistant` in that order.
4. **`MemoryPreferences.action(path, method, body, show)`** used to dispatch on the request path, and for `/review` also on `body.tool`, inside one 45-line `if/else` chain. Each caller now passes its own result handler: `showAdoptionPreview`, `showAdoption`, `showProposals`, `showDecision`, `showSearch`, `showClaim`, `showConnectionChange`. Each handler body is the original branch, moved unchanged. Handler errors still land in the same `catch`, because `action` awaits the handler.
5. **`FreshStores.change(request, done)`** replaces three copies of the busy, request, notice, reload, error, and unbusy flow in `choose`, `start`, and `remove`.
6. **`LifeOSSettings.runInstallationAction(url, succeed, failure)`** replaces eleven copies of the busy, status-clear, POST, success, failure, and unbusy flow. The callback bodies are unchanged (the diff shows them as context). The failure prefixes stay at each call site.
7. **Shadowing removed.** `MemoryImportReview.begin` named its request `source` and then looped `for (const source of current.sources)`; the request is now `origin`. The adoption click handler declared `const projects`, shadowing the SSH form's `projects` state; it is now `assigned`.
8. **`memoryWorkflowsEndpoint`** constant holds the release-manager workflow URL that was written out twice.

### Release bundle (`optional/lifeos_release_manager/dashboard/dist/index.js`)

- `Releases.action(identifier, name)` shadowed the `name` state ("Your name"). The parameter is now `step`. No other change.

### Tests

- New `tests/support/dashboard_sdk.cjs` (not matched by `tests/*.cjs`, so the runner does not load it as a test file). It provides `loadDashboard(bundle, { fetchJSON, window, globals })` with `preview()`, `mount()`, `unmount()`, plus `find`, `findAll`, `text`, `component`, `plain`, and `settle`. Each call has its own hook state. There is no shared mutable state between tests. Each test file keeps its own request mock, because the mocks describe different endpoint contracts.
- Converted all eight `tests/*.cjs` files. Test-specific mocks stay in place with their original lines.
- Added 13 tests, listed below with what each pins.

## Safety reasoning

- **Characterization before refactor.** Every changed bundle path got a test that passed on the unchanged bundles before I edited them (`checks.txt` sections 2 and 3a). The tests at HEAD are identical to the tests at `3ba2ed63`, so the same assertions guard the before and after states.
- **Mutation checks.** 19 single-line mutations of the refactored helpers and existing request shapes each made at least one test fail (`checks.txt` section 6). Examples: removing the busy reset, dropping the failure reason, changing POST to PUT, corrupting base64 bytes, dropping a read scope, removing the project filter, dropping the JSON header, not awaiting the result handler, skipping the store reload, and dropping the return prompt.
- **String literal comparison.** A literal count over both bundles, original against HEAD, shows no added or removed string literal (`checks.txt` section 7). The only changes are lower counts of `"POST"`, `"Content-Type"`, `"application/json"`, and dispatch keys (`"/adoption"`, `"/owner"`, `"/review"`, tool names) that the old path-based dispatch compared against. This covers visible text, class names, ARIA attributes, and endpoint paths.
- **Timing.** `action` now does `await show(result)`. For a synchronous handler this adds one microtask before `setBusy(false)`. React batches these state updates, so the effect is not observable in rendering. `start` and `choose` are no longer `async`, but they return the same promise from `change`, and `event.preventDefault()` still runs synchronously first.
- **No gate simplified.** Size limits, busy guards, the Discord removal acknowledgement, signature bindings, and the separate review and apply requests are unchanged.

## Tests

Commands, run from the worktree root with Node v22.22.3:

| Run | Command | Result |
| --- | --- | --- |
| Baseline at `728cd17a` | `node --test tests/*.cjs` | 42 tests, 42 pass, 0 fail, 0 skipped |
| Characterization, tests at `3ba2ed63`, unchanged bundles | `node --test tests/*.cjs` | 55 tests, 55 pass, 0 fail, 0 skipped |
| Final at HEAD | `node --test tests/*.cjs` | 55 tests, 55 pass, 0 fail, 0 skipped |
| Syntax | `node --check lifeos_hook_bridge/dashboard/dist/index.js` and `node --check optional/lifeos_release_manager/dashboard/dist/index.js` | both OK |
| Whitespace | `git diff --check` and `git diff --check 728cd17a HEAD` | clean |

I did not run any Python suite. This task changed no Python file, and `tests/support/` contains no Python module. These are SDK component fixtures, not browser, installed, or Discord tests.

Tests per file, baseline to final: `test_dashboard_ui` 6 to 8, `test_fresh_store_ui` 6 to 8, `test_memory_dashboard_ui` 11 to 15, `test_memory_portability_ui` 4 to 7, `test_memory_remote_ui` 6 to 7, `test_release_ui` 3 to 4, `test_memory_removal_ui` 3 to 3, `test_setup_presentation` 3 to 3.

New characterization tests:

| File | Test | Pins |
| --- | --- | --- |
| test_dashboard_ui | installation actions post once, stay busy, then report their result | All 12 installation buttons: exact `{method: "POST"}` init, every section button disabled while pending, exact success status text, exact follow-up GET sequence |
| test_dashboard_ui | installation action failures report the reason and release the busy state | All 12: `"Could not ...: " + reason`, no refresh after failure, button enabled again |
| test_fresh_store_ui | each store change reports its notice and reloads both statuses | Use, return, recover, remove, and start: exact init, notice text, reload order, busy while pending |
| test_fresh_store_ui | a refused store change shows the reason, skips reload, and enables controls | Error notice, no reload, buttons re-enabled |
| test_memory_portability_ui | profile file upload encodes each chosen file and reviews the uploaded source | Base64 of non-ASCII bytes, 1 MiB refusal, deselection, upload then preview then snapshot bodies with `source_identifier`, JSON headers |
| test_memory_portability_ui | portable bundle upload encodes the chosen file and reviews the uploaded source | 16 MiB refusal, `bundle_bytes` body, follow-up review |
| test_memory_portability_ui | a verified export prepares provider return with the reviewed prompt | Return workflow body `{kind, identifier, signature, plan_signature, prompt}`, headers, message, export plan decision body |
| test_memory_dashboard_ui | connection changes refresh memory status and report each outcome | Sharing toggle, DELETE revoke (headers kept, no body), enrollment with all optional scopes and project trimming, messages, status refresh after each |
| test_memory_dashboard_ui | review refusals report their reason and keep the previous proposal list | Search ok, then refused (results cleared), then status-only; proposal refusal leaves the list unloaded |
| test_memory_dashboard_ui | a committed decision reports a failed pending-change refresh | Three `/review` requests and their tools, combined message, proposal still shown |
| test_memory_dashboard_ui | a committed adoption reports a failed memory status refresh | Combined message, adoption preview cleared |
| test_memory_remote_ui | optional HTTP permissions extend the approved grant | Approve body with `principal`, `assistant`, `write_project`, trimmed projects, encoded request id |
| test_release_ui | a ready release is reviewed before its separate installation request | Review and apply are separate `{method: "POST"}` requests, review details shown, start message |

### Changed assertions and fixtures in existing tests

These are the request-shape and contract changes the parent asked to inspect:

1. `test_release_ui` "fresh page offers Install LifeOS": `JSON.parse(body).intent === "install"` became `deepEqual(body, {intent: "install", name: "User", assistant: "Hermes"})`. This is stronger.
2. `test_memory_dashboard_ui` "an unconfigured installation offers the owner claim": added the claim status message assertion.
3. `test_memory_removal_ui`: the old harness wrote `states[4] = true` to force the hidden `installed` state slot. The new harness mounts the real release page with a mock that answers `/installation` with `{installed: true}` and `/operations` with `{operations: []}`. The recorded calls now also include the page's two GET polls. All assertions select POST calls, so they are unaffected.
4. `test_release_ui`: the mock adds `/review` and `/apply` responses for the new test. `nodes(tree).find(...)` became `find(tree, ...)`. The old local `createElement` did not flatten children or default `props`; the shared one does both, like the other files.
5. `test_memory_portability_ui`: the panel window now provides `btoa`, which the upload paths need.
6. `test_memory_dashboard_ui`: the panel's fallback response may be a function, for the refresh-failure tests. Existing callers pass objects, as before.
7. `test_fresh_store_ui`: `controls()` accepts an optional refusal reason for the failure test.
8. `test_memory_remote_ui`: a missing component now fails with the harness message "The rendered page must include MemoryHTTPPreferences" instead of "The plugin must include HTTP memory setup".

### Harness behavior differences from the old per-file copies

- `preview()` and `mount()` always start from empty hook state. The old remote test rendered `MemoryPreferences` without resetting the slot index after the root render, so that preview read mismatched slots. The new preview is the correct one, and it only serves to locate the child component.
- `mount()` runs only the first effect it meets, which is the same rule as the old `effectRan` and `mounted` flags. The release test used to collect effects and run `effects[0]()` after the render. The effect now runs during the render, and its cleanup is kept for `unmount()`.
- Every load passes `console` into the context. Three files used to omit it. The bundles do not log.
- `useState` setters accept function updates in the release tests too. The release bundle does not use function updates.

## Scope inventory

Inspected in full:
- `lifeos_hook_bridge/dashboard/dist/index.js` (all 1398 lines)
- `optional/lifeos_release_manager/dashboard/dist/index.js` (all 262 lines)
- All eight `tests/*.cjs`
- Both `dist/style.css` files, compared with `diff` (byte-identical, not edited)
- `CONTRIBUTING.md`, the dashboard and test sections of `docs/codebase.md`, the audit follow-up section of `TODO.md`
- `~/.agents/AGENTS.md` (through the session instructions), `coding-rules/SKILL.md`, and `coding-rules/references/javascript.md`
- `git log` for the two bundles and the tests

Not inspected:
- Python dashboard APIs (`dashboard/plugin_api.py` in both plugins) and the Python test suites. I took request shapes from the bundles as they are; I did not compare them with the server routes.
- Both `manifest.json` files, except through `test_setup_presentation`.
- The Hermes host SDK source. Its contract is inferred from the existing test fixtures.
- Dated `docs/agents` and `docs/verification` material, except grep hits for `.cjs`. Some historical raw probes say they reuse "the existing SDK test harness". They are snapshots with their own copies, and this change does not alter them.

## Syntactic candidates and proved dead code

- A syntactic scan of both bundles for `const`, `let`, and `function` names that occur only once found **none**, before and after (`checks.txt` section 9). No `useState` setter is unused.
- **No code was removed as dead.** Every removed line was duplication, replaced by a shared helper with the same callers (`checks.txt` section 8). The old `path`/`tool` dispatch keys were not dead code. Each branch had exactly one caller, and each branch now lives in that caller's handler.

## Candidates rejected or deferred

| Candidate | Decision | Reason |
| --- | --- | --- |
| Identical `style.css` in both plugins | Rejected | Each plugin installs separately and its manifest names its own `dist/style.css`. Sharing needs a build step or a manifest change, and both are out of scope. |
| Release `MemoryWorkflows.act` and `prepareRemoval` duplication | Deferred | Only two copies. They carry request-counter race guards and different error resets (`setRemoval({})`). The gain is small and the race logic is subtle. |
| `refreshHostPatch` and `refreshLifeOSUpdate` polling | Rejected | Different contracts: the host poll retries on error up to 60 times; the update poll reports the error and stops. Different state lists and limits. |
| `Releases.refresh` versus the polling effect | Deferred | The effect also fetches installation status and uses an `active` guard. Merging them changes the mount logic. |
| Merging the parallel `MemoryImportReview` and `MemoryExportReview` structure (`run`, `draft`, `binding`) | Rejected | Different reset sets and binding keys (`snapshot_signature` against `signature`). This would be a broad restructure, not a bounded cleanup. |
| Constant for repeated class strings such as `rounded border border-border px-4 py-2 disabled:opacity-50` | Rejected | Churn across many render lines, with a risk to visible classes and no behavior benefit. |
| `MemoryPreferences.action` callers passing `undefined` as the body | Accepted as is | Three call sites. An options object would add indirection that the current positional form does not need. |
| Test helper for "button by label" with a clear missing-control message | Deferred | It would touch most assertion lines. It is worth doing as a separate, mechanical test-only change. |
| `docs/codebase.md` mention of `tests/support/` | Not done, out of ownership | Root docs are out of scope. The parent may add one line to the "Plugin presentation and request contracts" row. |

## Pre-existing behavior found (characterized, not changed)

1. **Known ownership activation gap (distinct tracked product issue, TODO.md).** `MemoryImportReview` still shows **Review publication plan** only when `Object.keys(decisions).length` is non-zero (bridge `index.js` line 198 at HEAD). An empty or no-import review cannot reach the activation path from the dashboard. I left this unchanged, as instructed.
2. **An oversize profile file clears the earlier valid choice.** A refused file throws inside `run()`. Its catch clears every upload, the review, the plan, and the publication. The browser's other file input still displays its earlier file, but the state no longer has it, so the upload button stays disabled until the owner picks that file again. The new upload test pins this behavior with a comment. It looks like a UX quirk rather than a security problem, because clearing private state on refusal is deliberate. Adrian should decide whether to keep it.
3. **A search refusal clears the shown search results.** `showSearch` always sets `results` to `result.results ?? []`. A proposal refusal, by contrast, keeps the previous proposal list. The two behaviors are inconsistent, and the tests pin both.

## Remaining review concerns

- **Riskiest change:** the `MemoryPreferences.action` handler split. It is the largest semantic move. Each branch has a characterization test, and the mutation of the `await` was caught, but the outcome tests run on the SDK fixture, not on React.
- **Decisions Adrian did not specify:** the handler names (`show*`, `runInstallationAction`, `change`, `postJSON`, `encodeFile`, `readScopes`, `projectNames`), the helper location `tests/support/`, and the use of `undefined` as the positional body in `action`.
- **Not covered by tests:** real browser rendering and the real host React hook semantics, polling timers past the first refresh, the authenticated `download()` export path (unchanged), and the agreement between the request shapes and the Python routes.
- **Shortcut taken:** the literal comparison and the unused-declaration scan are regex scans, not a parser. They are sufficient evidence for this diff, but not a lint pass. The repository has no linter configuration, and I installed none.
- **Attribute file:** `docs/agents/2026-10-16-dashboard-cleanup/.gitattributes` is the only configuration-like file I added. It affects whitespace checks for `data.diff` only.
- **Changes outside Git:** none. Temporary files exist only in `/tmp` (the mutation backup, the literal scanner, and run logs). Nothing global was installed or configured.

## Primary integration note

The primary agent preserves the original raw diff as `data.diff.gz`. Decompression reproduces `data.diff` byte for byte. The worktree-only whitespace attribute and launcher metadata are not part of the integrated change. The source commits retain the test-first sequence. The primary agent repeats all 55 component tests and both script syntax checks successfully on the integration branch. The original report above describes the isolated worktree.
