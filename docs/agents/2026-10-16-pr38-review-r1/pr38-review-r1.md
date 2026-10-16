# PR38 independent review, round 1

- Date: 2026-10-16
- Role: independent reviewer (single agent, no delegation, no memory or journal calls, read-only on product, tests, and Git index)
- Model: Claude Opus 5.5 (`claude-opus-5-5`), running in Claude Code
- Question: Is PR38 (`feature/codebase-cleanup`, base `455154c19611da320086592b98e15ead302817dc`, head `99e18c44`) correct, safe, free of unnecessary complexity, accurate in public documentation, and free of regressions? Which items block the 0.7.3 release?
- Raw evidence: `data.json` (commands and results), `evidence.tar.gz` (full test output, diffs, link audit), `removed-names.json`, `scripts/`.

## Verdict

**CLEAR.** I found no actionable defect introduced by PR38. The product changes are behavior-preserving refactors and import removals. The tests that I ran confirm the same results as the primary agent, with the limits below. No item that PR38 introduces blocks the 0.7.3 release. The release still needs exact-archive qualification, which is separate work (see "Release blockers").

## Findings

| ID | Severity | File:line | Cause | Reproduction | Status |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | No Critical, High, Medium, or Low defect introduced by PR38 | n/a | n/a |

Informational items (no action required for this PR):

| ID | File:line | Observation | Origin |
| --- | --- | --- | --- |
| N1 | `lifeos_hook_bridge/dashboard/dist/index.js:995-1001` | No test pins the install status text while the post-success refresh is pending. Same as r2 item I1. The callback bodies are unchanged since base. | Pre-existing |
| N2 | `tests/test_removal_generation.py:73` | The new characterization test asserts `KeyError('certificate')` from an intentionally incomplete fixture. It pins an incidental crash point after launcher matching, not a contract. A later change to request validation order could break this test without a product defect. | Introduced, test quality only |
| N3 | `tests/test_memory_atlas_capacity.py:178` | One transient failure ("The native job needs current local owner permission...") in my first runtime run. It did not reproduce in three later runs (head isolated, base isolated, full runtime rerun). The first run overlapped with `/tmp` quota exhaustion (EDQUOT) on this machine, caused partly by my own scratch exports and a concurrent 0.7.3 archive run by another process. I did not verify the cause. | Not attributable to PR38 |

## What I reviewed

### Hook command parsing (`lifeos_hook_bridge/bridge.py:179-255`)

`_hook_script` contains the exact token logic that the four recognizers duplicated at base: `shlex.split`, catch only `ValueError`, strip a leading `bun` launcher when exactly two tokens exist, and return the single remaining token. Each caller keeps its own guard and failure value: `_is_native_task_governance` keeps its `isinstance` check before parsing, `_native_post_hook` returns `""`, and the others return `False`. Non-string input reaches `shlex.split` in the same way as at base. The four new characterization tests in `tests/test_bridge_hook_commands.py` pass against the base `bridge.py` (4 of 4), so they describe pre-existing behavior.

### Launcher serialization (`optional/lifeos_release_manager/release_programs.py:20`)

`launcher_script` produces the same bytes as the five removed inline expressions (`release_worker.py:188,196`, `removal_generation.py:28,52`, `removal_preparation.py:63`). Each caller passes the same argument type as before: `release_worker.py:188` passes the raw request string, so a non-string still raises `TypeError` from `shlex.quote`, as at base. All callers load `release_programs` through relative imports from the same package directory. Retained removal sources copy the whole manager package, so the new name cannot be paired with an older `release_programs.py`.

### Unused imports and local assignment

An AST comparison of the 24 changed Python files finds 23 removed import bindings (21 unused imports, plus two `shlex` imports that `launcher_script` replaces). No head file loads a removed name (`removed-names.json`). A repository search finds no module-attribute access or `mock.patch` target for any removed name. The removed `active_bridge` assignment in `release_worker.py` had no other reference at base. `memory_policy.py` and `MemoryScope.as_dict` are unchanged.

### Dashboard bundles

- `postJSON`, `encodeFile`, `readScopes`, and `projectNames` produce the same request bodies, headers, and upload encoding as the inline code at base.
- `action(path, method, body, show)` at `index.js:508`: all ten callers pass an explicit handler. Each handler body matches the base branch that the old path dispatch selected. The proposal-decision refresh now uses `postJSON` with the same body.
- `change(request, done)` at `index.js:750` keeps the base order: busy, request, notice, load, then error and busy reset.
- `runInstallationAction` at `index.js:977` keeps the base order: busy, clear status, POST, success handler (returned refresh promises are still chained), failure prefix, busy reset. All eleven callers keep their base failure prefixes.
- Renames (`source` to `origin`, `projects` to `assigned`, release `name` to `step`) remove shadowing only.
- The head component tests pass against the base bundles (57 of 57). This shows that the tests describe preserved behavior.

### Test fixture (`tests/support/dashboard_sdk.cjs`)

The shared fixture loads the shipped bundles. It supports functional state updaters, which the old release-page harness did not. That is closer to React semantics and does not weaken any assertion that I found. It is not React and not a browser, as its header says.

### Documentation and release declarations

- All relative links and heading anchors in the 36 changed Markdown files resolve (`evidence/doc-links.json`). The 17 unresolved backticked paths are host paths, package-relative paths, or generic names, not links.
- README patch counts match `install_source.py` (10 Hermes, 25 LifeOS). README correctly keeps 0.7.2 as the stable published release while `VERSION` is 0.7.3.
- `release_version.versions()` returns `0.7.3` for the head tree. All five declarations agree. The 0.7.3 preparation commit follows the 0.7.2 pattern, except that it does not change the README stable line, which is correct before publication.
- CONTRIBUTING and the codebase map state the lifecycle patch-copy difference and the empty-review activation gap accurately. TODO tracks both.
- `git diff --check` over the range is clean. PR38 changes no patch file and no source declaration.

## Release blockers

None introduced by PR38. Baseline status, distinguished:

1. **Exact-archive qualification of 0.7.3 is not done.** `verification.json` records `release_qualification: false`. This is required before publication under the update policy. I observed another process running a 0.7.3 archive suite during this review. I did not inspect it and make no claim about its result.
2. **Lifecycle patch copies differ (baseline).** `scripts/build_managed_release.py` prepares LifeOS from `lifeos_hook_bridge/patches` (the distributed copy). Therefore the difference does not affect the release package. It blocks only use of `scripts/prepare_sources.py` output as a qualified substitute. PR38 does not change either copy.
3. **Empty or no-import ownership activation gap (baseline).** PR38 does not change this path. It is a known product limit, tracked in TODO. It is not a regression.
4. **Workstation release suite: two `/proc` process-inspection failures (baseline).** My run reproduces exactly the same two cases. I did not rerun the isolated service-account boundary tests; I rely on the primary agent's record for those eight passes.

## Tests actually run

All runs used disposable copies: `git archive` exports and `cp -a` copies of fixtures in `/home/outsider/.cache/pr38-review-r1-scratch/`. No shared extracted release tree was used for execution. Interpreter: frozen test environment Python 3.14.7 with `-B`. Node v22.22.3.

| Check | Result |
| --- | --- |
| `node --test tests/*.cjs` (head) | 57 tests, 57 pass, 0 fail, 0 skip |
| `node --check` both bundles (head) | exit 0, exit 0 |
| Head component tests against base bundles | 57 of 57 pass (first attempt failed 2 because my copy lacked `manifest.json`; corrected) |
| `test_bridge_hook_commands` against base `bridge.py` | 4 of 4 pass |
| Targeted Python: hook commands, release programs, removal generation, removal preparation, release configuration | 48 of 48 pass |
| Runtime suite (23 modules, same list as primary), run 1 | 391 run; 1 failure (N3), 15 skips (three hook variables were not set) |
| Atlas capacity module, head and base | 9 of 9 pass each |
| Runtime suite, run 2 with all hook variables | **391 run, 390 pass, 1 skip** (tagged read-only repository required) |
| Release suite (16 modules, same list as primary) | 150 run, 145 pass, 1 failure and 1 error (both known `/proc` cases), 3 skips |

The release run has two more skips than the primary record. Those tests need `LIFEOS_MANAGED_FRESH_OPERATION`, which points into a shared historical fixture. I did not use it.

## Limitations

- I did not run browser, installed-plugin, Hermes host, or exact-archive tests. Component tests use a minimal SDK fixture, not React.
- I did not repeat the 12 dashboard mutations or the isolated service-account boundary tests. I rely on the primary and r2 records for those.
- Two release tests that need the shared historical fresh-operation fixture were skipped in my run.
- I did not read every line of the 24 changed historical documentation snapshots. I checked their links and the claims in the active guides.
- I did not run a full static analyzer (no pyflakes, ruff, or flake8 is installed). The AST check covers only removed import names.
- My scratch exports contributed to `/tmp` quota pressure during the first runtime run. I moved them out of `/tmp` and reran.

## Changes outside Git

- Scratch directory `/home/outsider/.cache/pr38-review-r1-scratch/` (about 2.8 GB: exports and fixture copies). Remove it with `rm -rf /home/outsider/.cache/pr38-review-r1-scratch` when no longer needed.
- No edits to product, tests, the Git index, services, accounts, or shared fixtures.
