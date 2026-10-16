# Codebase cleanup and verification

- Date: 2026-10-16
- Role: primary implementation and verification agent
- Model: GPT-6.1 Sol, high reasoning effort
- Question: Which unused code and repeated implementation can we remove without changing supported behavior?
- Starting commit: `728cd17a94607ec4c119419c052060582a8b75af`
- Integrated product head: `a4c939550fe3c52d4785be9310c48dd122f53565`
- Branch: `feature/codebase-cleanup`

Adrian authorizes three Opus 5.5 cleanup agents through the `claude-delegate` skill. Each uses high effort and an isolated worktree. Two further Opus 5.5 runs review the dashboard change and its coverage fixes. All five runs finish. Their full reports and compressed raw evidence are retained below. The primary agent inspects the changes and repeats the relevant checks.

## Integrated changes

1. Remove 21 unused imports across runtime Python, release tooling, and two scripts. Remove one unused local assignment in the release worker. Project imports retain their module-loading side effects through remaining imports.
2. Extract the identical command parsing from four hook recognizers into `_hook_script`. Each recognizer retains its own path rules, input guard, and failure result. Four characterization tests precede the refactor.
3. Put exact account-launcher serialization in `launcher_script`. Installation and removal use the same byte format at five sites. Quoting, non-string behavior, file modes, and admission checks are characterized.
4. Consolidate repeated dashboard JSON requests, upload encoding, grant construction, busy/error flows, and installation actions. Replace path-based result dispatch with explicit result handlers at each caller. Visible strings, request shapes, styles, and approval sequences retain their contracts.
5. Share the Node dashboard SDK fixture in `tests/support/dashboard_sdk.cjs`. Endpoint-specific responders remain in their test files. The component suite grows from 42 to 57 tests.
6. Add the test helper to the codebase map. Keep full reports and raw evidence separate from active implementation guidance.

The primary rejects the proposed removal of `MemoryScope.as_dict`. It is a public method. Repository searches cannot establish the absence of external callers. `memory_policy.py` is byte-identical to the starting commit.

No upstream patch, version declaration, plugin manifest, frozen dependency, or release asset changes. No server selection changes. This branch includes the preceding local documentation cleanup.

## Reports and review decisions

- [Runtime worker](../2026-10-16-runtime-cleanup/runtime-cleanup.md): scans 137 runtime Python modules and traces dynamic consumers. Its original public-method removal is excluded during integration.
- [Release worker](../2026-10-16-release-cleanup/release-cleanup.md): scans 33 manager modules, 45 scripts, and 16 Bridge installation modules. It implements shared launcher bytes and records the existing patch-copy problem.
- [Dashboard worker](../2026-10-16-dashboard-cleanup/dashboard-cleanup.md): reads both bundles and eight component-test files. It implements local simplifications and characterization tests.
- [Independent dashboard review](../2026-10-16-dashboard-cleanup-review/dashboard-cleanup-review.md): finds no product defect and identifies three Low coverage gaps.
- [Review of coverage fixes](../2026-10-16-dashboard-cleanup-review-r2/dashboard-cleanup-review-r2.md): CLEAR. All three gaps are resolved.

The primary fixes the review findings in `6f22820a`:

- F1: hold installation controls busy until a post-success refresh finishes; catch its failure; clear previous status text on retry.
- F2: hold connection controls busy until the status refresh finishes and report refresh refusal.
- F3: show store success notices only after the request resolves. Replace a permissive missing-button assertion with an explicit existence check.

All 12 review mutations are detected after these fixes. The independent follow-up repeats that result and confirms the final tests pass against the pre-cleanup bundles. The primary independently reruns all 12 mutations in an exported copy.

One worker claim needs a qualification: the primary does not endorse the assertion that React batching makes an extra microtask unobservable. The independent reviewer measures one additional microtask for synchronous result handlers, with results set while controls remain busy. The reviewer finds that intermediate state benign. Real React scheduling remains outside this verification.

## Primary verification

The structured [verification receipt](verification.json) gives counts and limits. [primary-evidence.tar.gz](primary-evidence.tar.gz) preserves full output, exact commands, environment paths, source checks, and the disposable-account operator.

- Dashboard: 57 tests pass; zero skips. Both bundle syntax checks pass.
- Runtime and native hooks: 391 tests run; 390 pass and one tagged-repository test skips. The run uses the frozen Python closure, a disposable native-hook fixture, and an explicit replacement freshness control. The selected runtime and test inputs remain unchanged while unrelated release code is integrated.
- Release: 150 tests run on the workstation; 147 pass, one fails, one errors, and one sealed-current-package test skips. Both unsuccessful cases refuse inspection of the account's `sshd-session` process.
- Isolated process boundary: all eight consumer/coordinator tests pass under a disposable local service account. These include the two unsuccessful workstation cases. Assertions and product policy remain unchanged; source hashes match the integration tree. The account, home, and linger setting are removed.
- Import smoke: all 137 owned runtime modules import successfully in the frozen environment.
- Original component test names remain present. Static definition checks show no removed product function or class. Patch and version paths are unchanged.
- Working-tree and committed-range whitespace checks pass.

The release checks are covered across two account environments. There is no single clean 150-test workstation run. The initial worker runs retain their failures in the reports; the primary does not replace their evidence with later results.

The two skips require a tagged read-only repository and a sealed current package. The native checkpoint integration test is not run because it accesses the real workstation checkout and home. Checkpoint command recognition has direct characterization coverage. Installed browser acceptance, exact-package qualification, recovery from a newly built archive, and deployment remain separate release work.

## Fixture integrity and changes outside Git

The release worker's initial run generates bytecode in the local extracted 0.7.2 fixture. It removes that generated data. The primary's broader source checks generate 519 additional cache files despite `PYTHONDONTWRITEBYTECODE=1`. The primary removes only archive-unlisted `.pyc` files and the Hermes checkout fingerprint, then removes 95 empty cache directories.

The final check compares every one of the archive's 21,170 regular files with the extracted fixture. File contents and modes match, with no missing, additional, or unsupported entries. The archive remains 288,201,691 bytes with SHA-256 `293cfa2c6593b597c327fb8ad11f458d3e374352552dfbe7f4dbba5cd7e67265`. Directory modification times remain changed. No published asset is replaced.

The release worker removes synthetic test units leaked by its failed setup. It selects those units by its own fixture roots. The primary also stops one owned shell wait that matches its own `pgrep -f` expression. The exact intervention is retained in the raw evidence. The primary's isolated account is removed after the eight passing boundary tests. No persistent account or service setting is added.

The temporary worktrees and raw model responses stay outside the product tree. Branch commits preserve the implementation sequence. Private prompts and model responses are excluded from Git. The [fixture-integrity note](../../../notes/2026-10-16-cleanup-fixture-integrity.md) records the measured cache behavior.

## Deferred work and review focus

The two existing [TODO items](../../../TODO.md) remain separate product changes: lifecycle patch synchronization and an explicit empty/no-import ownership activation path. The release worker identifies the commits that changed only the distributed patch copy and proposes a regeneration/equivalence guard. Its source-preparation and patch-bundle failures must be resolved before a future complete release claims that path is qualified.

The audit preserves dynamically invoked OAuth methods, memory-provider methods, path-launched workers, older update/restore paths, and scripts whose bytes are pinned by historical evidence. Similar digest helpers serialize differently; several outputs are persisted signatures. These are unsafe candidates for automatic consolidation.

Static scans do not constitute a line-by-line logic review of the entire repository. Large memory modules and native TypeScript still warrant a separate focused review. Cross-module private helpers are a naming and ownership issue that needs a coordinated change. The independent dashboard review also records an unchanged success-message timing coverage gap as informational.

The main review areas are the hook-recognition helper, exact launcher bytes, and dashboard result-handler split. Their behavior is characterized, but the real host scheduler and a newly qualified installation are outside this batch. The code remains local on the feature branch; production continues to receive qualified releases.
