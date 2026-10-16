> Primary integration decision: `MemoryScope.as_dict` is retained. The worker report below records a proposed removal that the integration excludes. The primary stores the complete worker evidence in `evidence.tar.gz`, including the raw diff, checks, file inventory, and scripts. Broader parent checks use an explicit replacement control fixture; they do not restore the missing historical control or establish release qualification.

# Runtime Python cleanup

- Date: 2026-10-16
- Agent role: runtime cleanup worker for `lifeos_hook_bridge/` runtime Python (one of three parallel cleanup tasks)
- Question: Which unused code and bounded duplication in the owned runtime Python can be removed or simplified without changing behavior, and what evidence supports each change?
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Starting commit: `728cd17a94607ec4c119419c052060582a8b75af`
- Code head after changes: `442c7d6de5e540040ae7485c65f7dfea383f824b` (the report commit follows it; `commit.txt` has the final hash)

## Changes

Three code commits on `feature/runtime-cleanup`:

| Commit | Change |
| --- | --- |
| `f6960941` test(bridge): characterize hook script matching | New `tests/test_bridge_hook_commands.py`, 4 tests, written and passed against the original code before the refactor. |
| `d6a7be18` refactor(bridge): share hook script parsing | `bridge.py` gets a private `_hook_script(command) -> str \| None`. It does the split, optional `bun` removal, and one-token check that four functions repeated. |
| `442c7d6d` chore(memory): remove unused imports and as_dict | 13 unused imports removed from 13 files. Unreferenced `MemoryScope.as_dict` removed. |

Net code diff: 16 files, +90 / -46. Of that, 68 added lines are the new test file. `data.diff` holds the full diff from the starting commit, without this output directory.

### 1. Unused imports (13), all proved dead

| File | Removed name | Proof |
| --- | --- | --- |
| `memory_atlas.py` | `json_projection` (from `memory_sources`) | Never read in the module. No tracked file imports it from `memory_atlas`. Callers import it directly from `memory_sources`. |
| `memory_atlas_history.py` | `DATABASE` (from `memory_atlas`) | Never read. `SNAPSHOT` is still imported from the same module. |
| `memory_atlas_sync.py` | `CACHE` (from `memory_atlas`) | Never read. Other names are still imported from `memory_atlas`. |
| `memory_hypotheses.py` | `itertools.islice` | Never read. Standard library, so no side effect. |
| `memory_knowledge_conformance.py`, `memory_learning.py`, `memory_telos_template.py`, `memory_transition_probe.py`, `memory_user_index.py`, `memory_wisdom.py` | `pathlib.Path` | Never read in any of these modules. Standard library. |
| `memory_mcp.py` | `typing.Any` | Never read. The module uses `from __future__ import annotations`, and no annotation names `Any`. Script mode (`python memory_mcp.py`) still works: `--help` prints usage. |
| `memory_owner_jobs.py` | `NativeMemory` (from `memory_access`) | Never read. `JOB_OUTPUT_LIMIT` is still imported from `memory_access`, so the import of that module still happens. |
| `memory_recommend.py` | `json` | Never read. The scanner flagged a string reference, but that is only the `--json` CLI flag text and the `json_output` variable. |

Re-export and side-effect check (`checks.txt`, "Removal evidence"):

- An AST search covered every tracked `.py` file: `from X import name`, `X.name` attribute access, and exact string literals.
- A text search looked for `module.Name` patch targets.
- Neither search found a consumer of any removed name. The only hit is an unrelated `'CACHE'` literal in a dated `docs/verification` snapshot.
- Each removed project import came from a module that the file still imports for other names. So import order and side effects do not change.

### 2. `MemoryScope.as_dict` removed (proved dead)

- Commit `bc0f06b3` added it together with the dataclass. No caller has existed since then (`git log -S as_dict`).
- No tracked file references it outside its definition. The search covered source, tests, patches, TS, dashboard JS, optional plugins, and scripts.
- In the prepared 0.7.2 Hermes source, every `.as_dict()` call is on a Hermes-owned object. Hermes does not import bridge modules.
- `dataclasses.asdict` is still imported because `memory_policy.py:99` uses it.

### 3. Shared hook-script parsing in `bridge.py`

Before the change, these four functions each had the same 8-line block (`shlex.split`, then `ValueError` returns a failure value, then a 2-token `bun` launcher is stripped, then anything other than one token returns a failure value):

- `_is_native_version_drift`
- `_native_post_hook`
- `_is_native_checkpoint`
- `_is_native_task_governance`

The new `_hook_script` does those steps once and returns the script token or `None`. What each caller keeps:

- Its own failure value. `_native_post_hook` returns `""` and the others return `False`.
- `_is_native_task_governance` keeps its `isinstance(command, str)` guard before any parsing.
- Its own path rules: the literal `$HOME` set for version drift, `$HOME`/`~` rewriting against `root` for post hooks, the parts-suffix check for checkpoint, and resolved equality for task governance.
- The empty-token case: `'""'` gives `[""]`, and callers still receive `""`, because the check is `is None`, not a falsy test.

Why the characterization tests were needed: the only existing direct test, the `_native_post_hook` asserts in `test_async_native_delivery.py`, is gated on `LIFEOS_GUARD_SOURCE` and Bun. The other three functions had no direct tests.

What the new tests cover:

- Bare and `bun`/`/usr/bin/bun` launchers
- `node` and `bun run` refused
- Extra arguments
- Unterminated quoting
- Empty commands
- `$HOME`, `${HOME}`, and `~` spellings
- Out-of-root paths
- Unknown hook names
- Non-string input for task governance

Mutation checks in a temporary copy:

- Changing the token-count rule failed all 4 tests.
- Changing the `bun` name rule failed all 4 tests.
- Changing the malformed-quote result from `None` to `""` passed. That mutant is behavior-equivalent, because all four callers then return the same falsy result.

## Tests

Prerequisites I found and used. I installed nothing and changed no global settings.

- Workstation `python3` 3.14.8 has no `mcp` or `mcp_types`. The memory suites therefore need the frozen closure interpreter `/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python` (3.14.7).
- The environment variables copy `/home/outsider/.cache/lifeos-release-0.7.2-20261016/qualify_integration.py`: the 0.7.2 package `hermes/`, the 0.5.0 reference native fixture, the Bun 1.4.3 tool-bin, and the control installs. `tools/runtests.sh` has the exact values. It reads `RC_TREE` to select the tree under test.
- `LIFEOS_FRESHNESS_CONTROL_SOURCE`: the recorded path in `docs/verification/2026-10-04-hermes-learning-memory-flags/*.json` no longer exists. For a separate labelled run, I substituted `control-lifeos-install`, which is the `LIFEOS_HARVEST_CONTROL_SOURCE` value. That is a substitution, not the recorded control.
- To run the Bun-gated native hook suites, I made disposable reflink copies of the native fixture, one per run, and deleted them afterwards. The original fixture was never the target of a test.

Commands, run from the worktree root. `T=docs/agents/2026-10-16-runtime-cleanup/tools`:

```bash
# Memory set, 16 modules
$T/runtests.sh test_memory_policy test_memory_recommend test_memory_telos_template test_memory_transition_probe \
  test_memory_atlas test_memory_atlas_capacity test_memory_atlas_insight_edges test_memory_atlas_sync \
  test_memory_atlas_retention test_memory_hypotheses test_memory_knowledge_conformance test_memory_learning_ratings \
  test_memory_mcp test_memory_owner_jobs test_memory_user_index_publish test_memory_wisdom_frame
# Freshness-control substitute
LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-promotion-20261014/control-lifeos-install \
  $T/runtests.sh test_memory_hypotheses test_memory_learning_ratings test_memory_wisdom_frame
# Bridge set
$T/runtests.sh test_bridge_hook_commands test_bridge test_native_checkpoint test_native_task_hook \
  test_native_version_drift test_native_agent_invocation test_native_response_cache test_async_native_delivery
# Bun-gated native set: needs a disposable copy of the native fixture
cp -a --reflink=always <native fixture .claude> <scratch>/claude
$T/native_run.sh "$PWD" <scratch>/claude   # test_native_version_drift test_native_agent_invocation test_native_response_cache test_async_native_delivery
# Import smoke test of all 137 owned modules
PYTHONPATH=$PWD:<0.7.2 package>/hermes <frozen python> $T/import_all.py docs/agents/2026-10-16-runtime-cleanup/owned-files.txt
```

Results. "Baseline" means the starting commit. For the bridge and native sets, the baseline ran from a `git archive` copy of `728cd17a` plus the new test file.

| Set | Baseline | Final | Per-test comparison |
| --- | --- | --- | --- |
| Memory set | Ran 181, errors=6 | Ran 181, errors=6 | Identical |
| Freshness substitute (3 modules) | Ran 46, OK | Ran 46, OK | Identical |
| Bridge set | Ran 211, OK, skipped=16 | Ran 211, OK, skipped=16 | Identical |
| Bun-gated native set | Ran 15, OK, skipped=1 | Ran 15, OK, skipped=1 | Identical |
| Import smoke | 137/137 OK | 137/137 OK | Identical |
| `test_bridge_hook_commands` on original code | 4 OK | 4 OK | n/a |

Errors and skips:

- All 6 memory-set errors are `KeyError: 'LIFEOS_FRESHNESS_CONTROL_SOURCE'`: `test_memory_hypotheses` 4 (one test has 3 subtests), `test_memory_learning_ratings` 1, `test_memory_wisdom_frame` 1. With the substitute they pass on both trees.
- The 16 bridge-set skips are native suites without their source variables. The native set re-ran 15 of them with the scratch fixture.
- One skip remains, `test_native_version_drift.test_native_tagged_control_nags_once`. It needs `LIFEOS_VERSION_DRIFT_TAGGED_REPO_PATH`, which I did not have.
- I did not enable `test_native_checkpoint`. It creates a Git worktree in the real `~/workspace/LifeOS` and reads the real `~/.claude`, which this task must not touch.
- No run printed `Exception ignored` or `ResourceWarning`. All runs used `-W error::ResourceWarning`.
- `git diff --check` is clean.

Full raw output for every run is at the end of `checks.txt`.

## Candidates rejected or deferred

Syntactic candidates that are not dead code:

- `memory_oauth.MemoryAuthorization.register_client`, `load_authorization_code`, `exchange_authorization_code`, `load_access_token`, `revoke_token`: these are MCP SDK `OAuthAuthorizationServerProvider` protocol methods (`mcp/server/auth/provider.py` in the frozen closure), and the SDK calls them dynamically.
- `memory_provider.LifeOSMemoryProvider.system_prompt_block`: Hermes calls it through `agent/memory_provider.py` (`MemoryProvider` interface).
- `memory_mcp.create_server.AuthorizedConfiguration.load`: overrides `MemoryConfiguration.load`.
- `memory_algorithm_tab.view` (`fingerprints`, `directory`), `memory_diagnostics.read` (`relative`), `memory_return.cancel_preparation` (`plan`): unused names inside tuple unpacking. The unpacking documents the tuple shape. Renaming them to `_` is churn with no behavior value.
- `memory_http.py` `urllib` bound three times: these are distinct submodule imports (`error`, `parse`, `request`). False positive.

Deferred, with reasons:

- **Private helper coupling.** 141 cross-module imports of underscore names exist (`checks.txt`). Examples: `memory_sources._admit` (38 importers), `memory_tab_freshness._checked` (32), `memory_sources._source_time` (26), `memory_backup._read`/`_directory` (16/15), `memory_access._now` (15). These are de facto shared APIs. Making them public is a rename across about 40 files. It also touches files that other tasks own (`profile_backup.py`, `profile_backup_recovery.py`, `profile_services.py` import `memory_backup._read`/`_directory`), and it gives no behavior benefit. If you want this, it is a separate coordinated rename.
- **Canonical digest helpers.** `_digest`/`_signature` exist in at least 9 owned modules. They differ in serialization: `separators=(',', ':')`, `ensure_ascii=False`, `_encoded(...)`, or raw bytes. Some outputs are persisted signatures and journal fields. A shared helper would risk changing journal and signature formats. The only byte-identical pair is `memory_session_harvest._signature` and `ownership_setup._digest`. Merging those two would couple an ownership transaction module to a session-harvest module, or add a new shared module, for one line. Rejected.
- **Repeated source collectors.** `memory_manual_state._collect` and `memory_recommend.collect` share an 8-line window. The `memory_life_business`/`finances`/`health`/`work` modules follow the same admit-then-recheck shape. Each has different error messages and exception handling (for example, `memory_recommend` wraps `UnicodeError` in `MemoryUnavailable`, and `memory_manual_state` lets `UnicodeDecodeError` propagate). They also have different limits and domain checks. A shared collector would change exception types or messages, or it would need a generic parameterized abstraction. The task excludes both.
- **No module-level dead code found beyond the above.** In every owned module, all module-level functions, classes, and constants have at least one reference outside their definition, in the module itself or in other tracked code. The cross-reference search covered `.py`, `.ts`, `.js`, `.cjs`, `.yaml`, and `.patch`, and excluded dated docs. No private module-level name is unused. No statements are unreachable. All 137 owned modules are referenced by other code.

## Scope inventory

Inspected with AST and text tools (`tools/`):

- All 137 owned Python files in `owned-files.txt`. This is `git ls-files lifeos_hook_bridge/*.py` minus `dashboard/`, `patches/`, `bin/`, `install_source.py`, `installation_selection.py`, `lifeos_installation.py`, `native_dependencies.py`, `mount_transaction.py`, `program_lock.py`, `version_drift.py`, `profile_*.py`, `release_*.py`, and `update_*.py`.
- Scans run on all 137 files:
  - unused imports
  - unused module-level private names
  - module-level names unreferenced repository-wide or referenced only by tests and Markdown
  - unused locals and methods
  - unreachable statements
  - duplicate module-level bindings
  - identical function bodies
  - 8-line clone windows
  - cross-module private imports
  - modules with no importer

Read by hand:

- Import headers of all 13 edited files
- `bridge.py` lines 170-275 and every caller of the four hook helpers
- `memory_policy.py` header and `MemoryScope`
- `memory_mcp.py` header and `create_server`
- The flagged spots in `memory_algorithm_tab.py`, `memory_diagnostics.py`, and `memory_return.py`
- The digest helpers in 9 modules
- `memory_life_business.py` against `memory_life_finances.py`
- `memory_manual_state._collect` against `memory_recommend.collect`

Not inspected:

- Line-by-line review of the logic in the large owned modules (`bridge.py` beyond the hook helpers, `memory_access.py`, `memory_service.py`, `memory_preferences.py`, `memory_import.py`). I scanned them but did not audit them for logic simplifications.
- `memory_native.ts` and `memory_publication.ts`. These are not runtime Python. I did not check whether TS operations no longer have a Python caller.
- `plugin.yaml`, `native_capabilities.json`, and `dependency_locks/`. I only used them as reference corpora.
- Files owned by other tasks (listed above), `optional/`, and `scripts/`. I only used them as reference corpora.
- Other tests that import edited modules but that I did not run: the `test_memory_atlas_guest_recovery`, `test_memory_preferences`, `test_memory_sharing`, `test_sharing_component`, and `test_memory_portability_lifecycle` families. They cover the same modules through heavier fixtures.

## Remaining review concerns

1. **Riskiest change: the `bridge.py` refactor.** It sits on the hook path that decides version-drift skips, checkpoint skipping, task-governance detection, async tracker keys, and clock coalescing. Before and after, the characterization tests, the full `test_bridge` suite, `test_native_task_hook`, and the 15 Bun-gated native tests all give the same results. `test_native_checkpoint` did not run, so checkpoint recognition is covered only by the new unit tests.
2. **`MemoryScope.as_dict` was a public method.** I found no in-repo or Hermes caller. Code outside this repository and the 0.7.2 Hermes source could still call it in theory. I judged that unlikely, because scopes are created internally.
3. **Freshness control substitution.** The 6 tests that need `LIFEOS_FRESHNESS_CONTROL_SOURCE` passed only with a substituted control install. The recorded control directory is gone. Treat those 6 as "unchanged against a substitute", not as qualified.
4. **Environment drift.** The test interpreter is the frozen 0.7.2-era closure on Python 3.14.7, not the workstation 3.14.8.
5. **Changes outside Git.** I made temporary scratch fixture copies under `/home/outsider/.cache/lifeos-code-cleanup-20261016/runtime-cleanup-scratch-fixture` and a temporary tree at `/tmp/rc_head`. I deleted both. Scanner scripts remain in `/tmp/rc_tools`, and copies are in `tools/`. No configuration, global settings, or external systems changed.

## Files in this directory

- `runtime-cleanup.md`: this report
- `data.diff`: `git diff 728cd17a 442c7d6d`, which is the code and test diff without this directory. It is on disk but not committed: diff context lines for blank source lines end in a space, so committing it would fail `git diff --check` on the branch range. Regenerate it with `git diff 728cd17a 442c7d6d -- . ':!docs/agents/2026-10-16-runtime-cleanup'`.
- `checks.txt`: environment, commands, summaries, removal and caller evidence, scanner outputs, and full raw test output (trailing spaces stripped, as noted in its header)
- `owned-files.txt`: the 137 files in scope
- `tools/`: scanner scripts and test runners used for this report
- `commit.txt`: final branch commit hash. I wrote it after the report commit, and it is not committed.
