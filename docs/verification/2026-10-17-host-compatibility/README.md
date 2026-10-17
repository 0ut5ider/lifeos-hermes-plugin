# 2026-10-17: Hermes compatibility detector

Role: primary agent, Cerebo. Model: Claude Opus 5.5. Question: does the read-only compatibility detector classify real Hermes installations correctly, and does it leave them unchanged?

This record covers step 1 of the [in-place installation plan](../../in-place-installation-plan.md). It does not qualify an installer. **Install LifeOS** does not use the result yet.

## What was built

- `optional/lifeos_release_manager/host_compatibility.py` inspects the Hermes source that the running interpreter imports. It checks the layout, the exact Git commit, the SHA-256 hash of every patch target, the Git working tree, profiles, and Python dependencies. It reports every blocking reason.
- `optional/lifeos_release_manager/host-compatibility.json` binds Hermes `v0.21.7`, commit `71d34bad1045610252eda02ee79549436896e784`, the ten canonical patch hashes, the stock and patched hash of each of the 94 target paths, and the four bridge dependency pins.
- `scripts/build_host_compatibility.py` generates the manifest from the qualified `stock-hermes.tgz` (SHA-256 `216eaa0a95b4cb324b8b024a4458cd5c50a82b156ce5305f8069e3e2fa09c5a9`, the same value that `DAILY-CANDIDATE.json` records for package `0.7.3-70fa8390`). The generated hashes equal all 94 before and after hashes in the [Opus review data](../../agents/2026-10-16-minimal-install-review/review-hermes-changed-files.json).
- `hermes lifeos-release compatibility` prints the result. Its exit status is 0 only for a compatible installation.
- The owner-only dashboard endpoint `GET /api/plugins/lifeos-release-manager/compatibility` returns the result. The LifeOS releases page shows it in the **Hermes compatibility** section.

## Decisions

- File hashes are the authority for the 94 patch targets. `git apply --check` accepts an edit outside the hunk context, so it is not sufficient.
- Untracked files that Git does not ignore cause a refusal. Ignored files, such as the virtual environment, do not.
- Tracked files that Git hides with `skip-worktree` or `assume-unchanged` cause a refusal.
- Git runs with `--no-optional-locks` and `GIT_OPTIONAL_LOCKS=0`. A mutation test shows that, without these, `git status` rewrites `.git/index`.
- Named profiles cause a refusal (`shared_installation`). The first supported layout is a single-profile installation.
- An install stamp is a packaged build only when it names a distribution or an update mechanism other than `self`. The stock Git bootstrap writes a stamp with `distribution: null` and `updateMechanism: "self"`. The first version of the detector treated any stamp as packaged, and the `.213` result showed that this was wrong.

## Tests

The suites run with the frozen 0.7.3 test environment and the qualified patched Hermes tree on `PYTHONPATH`.

| Suite | Result |
| --- | --- |
| `test_host_compatibility.py` | 26 tests pass |
| `test_host_compatibility_manifest.py`, with `LIFEOS_STOCK_HERMES_ARCHIVE` set | 8 tests pass; the manifest equals a rebuild from the stock archive |
| `test_release_manager_cli.py` | 9 tests pass |
| `test_release_dashboard.py` | 5 tests pass, 1 existing skip that needs `LIFEOS_MANAGED_FRESH_OPERATION` |
| `test_release_ui.cjs` and `test_memory_removal_ui.cjs` | 12 tests pass |

Mutation checks: removing the hash check fails 5 tests. Removing the hidden-change check fails 1 test. Removing the optional-lock settings fails the read-only test.

## Real upstream checkout

A shallow fetch of upstream commit `71d34bad` gives these results:

| State | Result |
| --- | --- |
| Clean stock checkout | `compatible` |
| First patch group only | `partially_patched`, 15 paths |
| All ten patch groups | `patched_without_record` |
| Comment appended to `model_tools.py` (a patch target) | `modified_source`, `model_tools.py` |
| Line appended to `README.md` (not a patch target) | `modified_source`, `README.md` |
| All changes reverted | `compatible` |

## Real hosts

Each run copies only the detector and the manifest to a temporary directory and starts the host's own Hermes interpreter as the service account. The `.git/index` modification time and size are the same before and after each run. Each host has no temporary directory left after the run.

| Host | Source | Result | Raw data |
| --- | --- | --- | --- |
| Development, `192.168.8.252` | Managed 0.7.3 runtime | `modified_source`: 3 untracked release files, and `patched_without_record` | [JSON](development-252.json), [meta](development-252.meta.json) |
| Daily, `192.168.8.253` | Managed 0.7.3 runtime | `modified_source`: 3 untracked release files, and `patched_without_record` | [JSON](daily-253.json), [meta](daily-253.meta.json) |
| Hermes agent, `192.168.8.213` | Root Git install at `/usr/local/lib/hermes-agent` | `unsupported_version`: commit `f4795c92`, a `v0.21.4` canary build | [JSON](hermes-agent-213.json), [meta](hermes-agent-213.meta.json) |

The development and daily results are correct. The managed release already patched those trees, and they have no in-place installation record. The plan's managed-release transition (step 5) must handle them. The `.213` installation needs a qualified entry for its Hermes version, or a move to the qualified `v0.21.7` commit, before LifeOS can patch it.
