# Minimal plugin installation review

- **Date:** 2026-10-16
- **Role:** Read-only architecture and code reviewer (subagent). No product files, branches, servers, memory, or journal were touched.
- **Model:** Claude Opus 5.5 (`claude-opus-5-5`), high effort as selected by the parent.
- **Question:** Can the release stop shipping complete Hermes and LifeOS, so a user installs only a plugin through Hermes, and activation fetches and patches LifeOS and applies reversible compatibility patches to the existing Hermes installation? Evaluate options A to E and their combinations.
- **Inputs:** repository at `f231c305` (`feature/release-073-deployment`), the qualified archive `0.7.3-70fa8390.tgz` (sha256 `2deae5dc...49c8`, verified equal to the certificate), and `package-size-breakdown.json`. Raw data: `data.json`, `review-measure-raw.json`, `review-git-experiments-raw.json`, `review-hermes-changed-files.json`, `review-commands.md`, `scripts/`.

## 1. Short answer

Yes, the release can stop shipping complete Hermes and LifeOS, and most of the transfer cost is avoidable. The cheapest safe path does not edit the user's Hermes files, though.

- About 251 MB of the 288 MB archive is the same Hermes base stored three times: the patched worktree (81.6 MB gzip), a shallow one-commit `.git` pack of that tree (88.2 MB), and `stock-hermes.tgz` (81.2 MB). The Hermes delta itself is 94 files, 1.0 MB as gzip, or 86 KB as the ten patches.
- On a disposable copy, applying the ten distributed patches to the unversioned stock tree reproduces the qualified patched tree byte for byte (E1). Reversing them reproduces stock byte for byte (E3). So the patched tree does not need to be shipped; it can be derived and verified by hash.
- The highest-value, lowest-risk change is **B + C**: keep today's integration-owned private runtime and reviewed apply, rollback, and removal transactions, but build that runtime from the user's local Hermes base commit when one is present (B), and otherwise from split, digest-addressed component assets reused across releases (C). By measured component sizes, first install falls from about 290 MB of release assets to about 101 MB (or about 18 MB when the base commit exists locally). Updates with unchanged bases fall to about 2.6 MB. Bun and Python wheels are extra in every option and I did not measure them.
- **Option A (in-place patching of the user's Hermes)** is technically feasible for exactly one layout: a clean, user-owned default-installer Git checkout at `71d34bad`, with every Hermes process under systemd control. Code for it already exists from the earlier bridge-first design (`install_source.py:468-757`) but it has real gaps (sections 6.1 and 9). Its unavoidable problem is Hermes's own `hermes update`, which stashes and reapplies local changes: in my Git simulations the patches either carried silently onto an untested commit or were dropped on conflict, and the stock updater then resets to clean code and keeps going (E9b to E9d; `update_cmd_stash.py:448-496`). I recommend A only as an opt-in restricted proof after B + C, if Adrian specifically wants the user's own install modified.
- **Option D (stock Hermes, plugin only)** cannot provide lasting-memory ownership, prompt admission, command-policy decisions, final-answer gates, or per-child routing without host changes. It is useful only as an explicit, labeled outcome for unsupported versions. It must not be the silent fallback it is today (`__init__.py:54-80`).
- **Option E (upstream hooks)** is the only route to arbitrary-version compatibility. A runtime import overlay is an untested hypothesis.

No option makes arbitrary Hermes versions compatible. Each Hermes base still needs a ported and qualified patch set. Unknown versions need a defined refusal (section 8).

## 2. Recommendations, ordered by compatibility and verification risk

Ordering follows dependency first, then ease of verification, then risk of subtle bugs, then blast radius.

1. **C1: Split the package into digest-addressed components and derive the patched trees at preparation.** It unblocks everything else. It is easy to verify: the derived Hermes and LifeOS trees must equal today's `tree_sha256` manifests, and E1 already shows Hermes equality. Blast radius is contained to preparation; apply, rollback, and removal are unchanged. Effort: touches `build_managed_release.py`, `release_catalog.py`, `release_stage.py`, `install_source.py` validators, the certificate format, and their tests. Expect two iterations, because validators currently require Git metadata (F8).
2. **C2: Cache Bun and component assets by digest across operations, and add retention for superseded operations.** It is easy to verify (digest equality), with low risk. Today every preparation downloads the archive, dashboard, and Bun again (F12), and no job cleanup exists.
3. **B: Derive the Hermes base from the user's local Git object store when the exact base commit exists** (detached worktree, `git archive`, or reflink copy), and fall back to the C1 stock asset. Verification: same tree digest as C1. It never reads the user's working tree, so local edits are irrelevant. The risk is in edge cases: partial clones, shared object stores, and a selected base older than the user's running Hermes (an explicit downgrade decision).
4. **D-explicit: Replace the silent reduced-mode registration with an explicit, owner-visible state.** The bridge should refuse patched-mode claims, and refuse turns when the profile's receipt expects a patched host but the host lacks the hooks. It is easy to test with stock and patched fixtures. This is a behavior change, so Adrian decides the policy (warn or fail closed).
5. **E-upstream: Propose the generic host extensions upstream** (required middleware, prompt admission, command approval decision, pre-delivery stop gate, turn result, outbound delivery check, per-child route, provider-fallback flag). Long schedule, and outside our control.
6. **A-restricted: In-place patching as an opt-in for one exact base and one layout.** Do it only after items 1 to 4, with the controls in section 6.1. Hardest to verify (process inventory, `hermes update` interaction, other profiles and plugins) and widest blast radius (it changes the shared Hermes used by every profile and plugin).
7. **E-overlay: an import-time overlay.** Do not pursue it before a bounded probe; every property of it is unverified.

## 3. What the current design does

### 3.1 Initial install is already small

The GitHub subdirectory bootstrap installs `optional/lifeos_release_manager` only (`README.md`, `docs/installation-workflow.md:22-46`). The whole `optional/` directory compresses to 76,535 bytes. The manager registers a CLI command and a skill (`optional/lifeos_release_manager/__init__.py:6-11`). The large transfer happens at **Install LifeOS**, not at plugin install.

### 3.2 First use and every update transfer the complete package

`ReleaseCatalog.download` fetches the certificate, the full archive, and `hermes-dashboard.tgz` for every preparation (`release_catalog.py:144-185`). `prepare_runtime` downloads Bun again into each job (`release_stage.py:200`, `release_tools.py:18-53`) and builds a frozen Python environment from the packaged lock (`release_stage.py:204-209`). For 0.7.3 the release assets alone are 288,173,954 + 1,542,030 + 4,225 = 289,720,209 bytes, plus 42,015,103 bytes of Bun, plus unmeasured wheels and LifeOS native packages. **Update LifeOS** and **Update plugin** select the same complete package (`docs/installation-workflow.md:104`), so a plugin-only change costs the same transfer.

### 3.3 Runtime ownership

The integration owns a private runtime per operation. `prepare_runtime` copies the complete patched tree, `.git` included, into `<profile>/.lifeos-releases/<id>/hermes` (`release_stage.py:214-223`). It assembles a contained Hermes payload there (`release_payload.py:16-55`). `_program_plan` then replaces the service launchers and `~/.local/bin/{hermes,hermes-agent,hermes-acp}` with `exec <job>/bin/<name>` wrappers (`release_worker.py:185-199`). The user's original Hermes checkout is left on disk and is no longer selected.

### 3.4 On-disk size per retained operation (estimate)

Each retained operation keeps the archive, the extracted package, and the runtime copy. `inspect_operation` re-hashes the archive (`release_plan.py:22-27`), and rollback and removal read the package (`removal_generation.py:55-58`). From measured component sizes, that is at least 288 + 448 + 303 + 42 (Bun archive) ≈ 1.08 GB per operation, before the venv, Bun binary, reference `.claude`, and pm runtime. I found no retention cleanup (F12). This is a code-path estimate, not a measurement of an installed system.

### 3.5 Removal

Removal does not return to the user's original install. It builds a second, stock runtime from the packaged `stock-hermes.tgz` and repoints the launchers to it (`removal_preparation.py:136-144`, `release_stage.py:214-221`). It requires a verified provider return first (`removal_preparation.py:9-35`), and it refuses accounts with additional profiles (`removal_generation.py:16-24`).

### 3.6 Admission and memory

Lasting-memory ownership fails closed when the host lacks `REQUIRED_MIDDLEWARE_API_VERSION` (`memory_provider.py:36-43`, `memory_provider.py:99-115`). Command, prompt, and stop policy degrade silently: if the patched hooks are missing, the bridge registers the stock subset and returns (`__init__.py:54-80`). Stock `register_hook` accepts unknown names with only a warning (stock `hermes_cli/plugins.py:933-955`).

### 3.7 Update guard

Nothing in the integration code prevents `hermes update`. The guard is documentation (`docs/update-policy.md:20`, `docs/installation-workflow.md:106`). The managed runtime keeps `.git`, so stock Hermes treats it as a dev checkout (`_launchers.py:872-883`). Its `origin` points at a builder-local cache path. I did not run `hermes update` against a managed runtime, so the actual outcome there is untested.

### 3.8 The earlier in-place path

An earlier bridge-first in-place path still exists. The bridge dashboard exposes prepare, apply, restore, and recover endpoints for a host patch (`plugin_api.py:1328-1425`). They call `stage_hermes_patch`, `apply_hermes_patch`, `restore_hermes_patch`, and `recover_hermes_patch` (`install_source.py:468-673`) through a detached `systemd-run` worker (`plugin_api.py:1348-1366`, `install_source.py:723-780`). The historical guide says this path completed an API apply and restore on a separate account but lacked browser acceptance (`docs/history/2026-10-16-installation-workflow.md`, item 5). That is a historical claim; I did not re-verify it.

### Input corrections

- `release_validation.py`, named in the brief, does not exist at HEAD (`git ls-files` returns nothing).
- `README.md` still names 0.7.2 as the stable release, while `VERSION` and both `plugin.yaml` files say 0.7.3.

## 4. Measured facts

All figures come from the disposable extraction. gzip figures are independent `tarfile` streams at compresslevel 9, the builder's default. They sum to 287,980,867 bytes, within 0.07 percent of the real archive, so they are fair attributions, but not guaranteed savings.

| Component | Uncompressed bytes | gzip-9 bytes |
|---|---:|---:|
| Hermes worktree, patched, without `.git` | 213,770,704 | 81,550,670 |
| Hermes `.git` (shallow, 1 commit, 19,262 objects) | 89,642,568 | 88,235,209 |
| `stock-hermes.tgz` (as stored) | 81,180,515 | 81,180,515 |
| LifeOS worktree, patched, without `.git` | 29,341,247 | 15,946,547 |
| LifeOS `.git` (717 commits) | 18,113,982 | 17,696,330 |
| `lifeos_hook_bridge` (all 36 patches included) | 9,644,196 | 1,953,166 |
| of which the patch files | n/a | 1,406,849 |
| `tests` | 4,362,602 | 832,734 |
| `python-runtime` (lock and pyproject only, no wheels) | 1,257,861 | 388,878 |
| `optional`, `scripts`, `docs` | 314,179 / 461,296 / 17,332 | 76,535 / 113,522 / 6,761 |
| Integration only (bridge, manager, closure, scripts, docs, root files) | n/a | 2,565,246 |
| Hermes overlay: all 94 changed files | 3,781,668 | 1,022,795 |
| Hermes overlay: 58 non-test changed files | 3,254,452 | 902,757 |
| Ten Hermes patches | n/a | 86,215 |

**Hermes delta.** Stock has 18,243 files. The patches modify 68 files and add 26, removing none. By category: 55 are in wheel packages, 2 are root modules (`cli.py`, `model_tools.py`), 36 are tests, and 1 is `scripts/run_tests.sh`. No patch touches `pyproject.toml`, `uv.lock`, `web/`, or compiled dashboard assets.

**LifeOS delta.** 218 files modified, 55 deleted, and 60 untracked. 110 file sections of `lifeos-content-response-consumption.patch` (6.18 MB) rewrite compiled Pulse output under `PULSE/Observability/out/_next`.

**Python closure.** The qualified `uv.lock` equals the stock lock plus three entries: the bridge's plugin metadata package, `tree-sitter 0.26.0`, and `tree-sitter-bash 0.25.1`. Nothing was removed.

**Patch copies.** All 36 distributed patches are byte-identical to the package copies. Only the documented `hermes-session-lifecycle.patch` differs between `patches/` and `lifeos_hook_bridge/patches/`.

### Experiments on disposable trees

| ID | Experiment | Result |
|---|---|---|
| E1 | Forward-apply the 10 patches to the unversioned stock tree | All applied. The tree equals the qualified patched tree: 0 missing, 0 extra, 0 different. |
| E2 | Forward `--check` on the qualified tree | All 10 refuse. The reverse series check passes. "Already patched" is detectable. |
| E3 | Reverse the series on the qualified tree | Equals stock exactly. |
| E4 | Edit a line inside a hunk (`plugins.py` `VALID_HOOKS`) | The first patch refuses at `hermes_cli/plugins.py:108`. Nothing applies. |
| E5 | Append a comment to `model_tools.py` (outside the hunks) | All patches apply. The file then differs from the qualified hash. Reverse restores the edit byte-exactly. |
| E6 | Wheel-like subset (2,216 files from the setuptools include list) | The unfiltered series fails on missing `tests/`. With `--exclude=tests/* --exclude=scripts/*` it applies and matches the qualified runtime files. This is a simulation, not a real wheel. |
| E7 | Copy the stock tree on btrfs | Reflink 1.16 s, plain copy 3.5 s. One warm run; shared extents not measured. |
| E8 | `git worktree add --detach` at the base plus the patches | About 2 s. All applied. The primary checkout stays clean. |
| E9a | `git stash push -u` then `stash apply`, same base | The patch state is restored identically. |
| E9b | Upstream commit adjacent to a hunk, then stash apply | Merges without conflict. The patched files now sit on an untested commit. |
| E9c | Upstream commit in an unrelated file, then stash apply | Succeeds. HEAD is no longer the qualified base. |
| E9d | Upstream commit overlapping a hunk, then stash apply | Conflict in `hermes_cli/plugins.py`. The stock updater resets to clean and parks the stash (`update_cmd_stash.py:448-496`). |

E9 simulates Git behavior only. I did not run the Hermes updater.

### Existing tests

38 tests ran across `test_hermes_install_source` (10), `test_release_programs` (23), `test_stock_hermes` (4), and `test_latest_hermes` (1). 37 pass. `test_latest_hermes` passed its prepare and validate steps against a disposable clean clone at the base, then failed its import check with `ModuleNotFoundError: No module named 'ruamel'`, because system `python3` lacks Hermes dependencies. That is an environment limit. Logs: `review-existing-tests.stderr.gz`. The in-place tests use a synthetic Git repository and callable stubs for stop, start, and verify. They prove the journal logic, not real service or process behavior.

## 5. Options comparison

"Transfer" means bytes from release or upstream hosts. Figures are sums of measured components, rounded. Bun (42 MB per preparation today), Python wheels, and LifeOS native packages are excluded everywhere and were not measured.

| Dimension | Current | A in place | B local base, private runtime | C split assets, private runtime | D stock plugin only | E upstream |
|---|---|---|---|---|---|---|
| Initial plugin install | 77 KB manager | Bridge-sized, ~2 MB | 77 KB manager | 77 KB manager | ~2 MB bridge | Plugin only |
| First-use transfer | ~290 MB | LifeOS (~16 MB asset or upstream fetch) + ~2.6 MB | ~18 MB with local base; C figures otherwise | ~101 MB (81.2 stock + 15.9 LifeOS + 2.6 + 1.5 dashboard) | LifeOS + bridge | LifeOS + plugin |
| Update transfer, bases unchanged | ~290 MB | ~2.6 MB | ~2.6 MB | ~2.6 MB | ~2 MB | Plugin |
| Update transfer, new Hermes base | ~290 MB | New patches; host update is Hermes's own | Local fetch of the new base or a new stock asset | New stock asset (~81 MB) | n/a | n/a |
| On-disk per operation | ≥1.08 GB (estimate) | ~3.2 MB of retained before-files | Runtime copy (near zero source cost with reflink on CoW; ~214 MB otherwise) + venv | Same as B without the reflink option, minus duplicate packaging | None beyond plugin and LifeOS | None |
| Runtime owner | Integration (private, per job) | Shared: user, Hermes updater, integration | Integration (private) | Integration (private) | User / Hermes | Hermes |
| Arbitrary-version compatibility | None | None; exact base only | None; exact base only | None; exact base only | Any version with the used stock hooks, reduced features | Possible if the hooks become stable API |
| Existing support | Qualified 0.7.3 | Partial, with gaps (F1 to F5) | Partial (`prepare_hermes` clones a local repo at the pin, `install_source.py:216-250`) | Partial (digests, `tree_sha256`, stock identity) | Reduced registration exists, but is silent | None |
| Measured proof here | n/a | E1 to E5, E9 (disposable only) | E1, E7, E8, test prepare path | Component sizes, E1 | Hook-set diff only | None |
| Main risk | Size, disk | `hermes update` collision, shared blast radius | Base selection edge cases | Identity and validator changes | Safety contract not met | Upstream schedule |

## 6. Option details

### 6.1 Option A: compact bootstrap, exact upstream fetch, reversible in-place Hermes patches

This is the user's preferred design. It is feasible for a restricted layout. The specification below is what it would take to keep admission, memory, cancellation, update, and removal behavior. Items marked **gap** are missing from the existing code.

**Supported layouts (first proof).** Exactly one: the default Linux installer's Git checkout at `$HERMES_HOME/hermes-agent` (stock `scripts/install.sh:23-27`, `scripts/install.sh:85`), owned by the user, with HEAD `71d34bad1045610252eda02ee79549436896e784`. Every process that imports that checkout must run under systemd user units the worker can stop: gateway, dashboard, and any cron or job runners.

Refused, with an explicit reason:

- Docker, Nix, and desktop-app stamped installs, which have an external steward and may be read-only (`version_info.py:1-10`, `version_info.py:185-186`, `_launchers.py:872-883`).
- ZIP installs without `.git` (`update_lock.py:1-16`).
- pip or pipx site-packages, which are not a declared distribution in `version_info.py`. E6 suggests runtime-only patches could apply, but the private-runtime builder needs `pm/` and `scripts/build`, which wheels lack.
- Root-owned or multi-account installs. The plugin never escalates.
- Foreground or unmanaged processes.

**Exact identity.**

- HEAD must equal the base.
- The 68 modified paths must hash to their stock values, and the 26 added paths must be absent. The before and after hashes for all 94 are in `review-hermes-changed-files.json`.
- The rest of the tree must be clean. The existing `stage_hermes_patch` requires `git status --porcelain --untracked-files=all` to be empty (`install_source.py:477-480`). That is strict, but it is the honest condition for "this is the qualified tree".

**Local edits and already-patched trees.**

- Admit by file hash, never by `git apply --check` alone. E5 shows a patch applies cleanly over a local edit and yields an unqualified file.
- An edit inside a hunk is refused (E4). An edit anywhere else in the 94 files is refused by the hash rule.
- An already-patched tree with our journal and matching after-hashes is "applied", and the operation is idempotent.
- A tree matching our after-hashes without our journal is "foreign identical". Adopt it only with owner review, never automatically.
- A partially patched tree is refused.
- No path deletes or overwrites a local change.

**Root access and multiple profiles.** One checkout serves every profile under `~/.hermes/profiles` and every plugin in them. Patching changes plugin dispatch, approval, delivery, and turn code for all of them. The worker must enumerate every profile and every unit using the checkout, and refuse while any cannot be stopped. Removal already refuses multiple profiles (`removal_generation.py:16-24`). A should start with the same restriction.

**Admission and reverse admission.**

- Forward requires all 94 before-hashes, the base HEAD, no foreign journal, no active release, removal, or memory operation (mirror `release_worker.py:61-77`), and current installation-owner authority.
- Reverse requires all 94 after-hashes. The existing `restore_hermes_patch` refuses otherwise (`install_source.py:617-619`), which is correct.
- If later edits exist, offer an owner-reviewed reverse-patch alternative. E5 shows reverse preserves edits outside hunks. Report the result as "restored with local edits", not as stock.

**Atomic prepare versus loaded modules.** Preparation is fully off-line from the running system: stage after-files and retained before-files in a private snapshot. Writing files under a running interpreter is unsafe. Hermes imports many modules lazily, so a running process can import a patched module into an unpatched process. So:

1. Stop every consumer.
2. Publish the files.
3. Start the consumers.

There is no immediate activation without a restart. **Gap F2:** the existing worker stops and verifies only `hermes-gateway.service` (`install_source.py:729-757`). The dashboard that launched it, and any CLI session, keep running old code.

**Controlled restart and verification.** Restart every stopped unit and require new PIDs. In each new process, verify that `VALID_HOOKS` contains the patched hooks and that `REQUIRED_MIDDLEWARE_API_VERSION == 1`; `test_latest_hermes.py:24-30` shows the probe. **Gap F3:** `_verify_gateway` checks activity, a new PID, and `hermes config check` only (`install_source.py:703-720`).

**Crash recovery.** Reuse the journal states (`staged`, `applying`, `applied`, `restoring`, `rolled_back`, `*_failed`) and `recover_hermes_patch` (`install_source.py:648-673`). **Gap F4:** `_write_patch_state` and `_write_patch_files` do not fsync files or directories (`install_source.py:449-459`, `install_source.py:524-541`). `ProgramTransaction.publish` does (`release_programs.py:25-48`). Use `ProgramTransaction` file entries for the 94 paths; its later-edit refusal and retained before-copies already match this need (`release_programs.py:177-400`).

**Concurrent Hermes updates.** Hold Hermes's own checkout lock (`<git common dir>/hermes-update.lock`, stock `update_lock.py:135`) and honor the update marker for the whole transaction, plus our `installation_lock`. That this fully excludes `hermes update` is a hypothesis from the docstring (`update_lock.py:1-16`); I did not test it.

**Upstream self-update interaction.** This is the decisive risk. Stock `hermes update` autostashes local changes, pulls, and reapplies (`update_cmd_stash.py:88-100`, `update_cmd_stash.py:448-496`). In Git simulation:

- An adjacent or unrelated upstream change carries the patches silently onto an untested commit (E9b, E9c).
- An overlapping change conflicts (E9d). Hermes then resets to clean upstream, parks the stash, and continues the update.

In both cases the integration's qualified identity is gone. Policy silently drops to reduced mode (F5), and memory turns unavailable (F6, and stock `agent/agent_init.py:1343-1371` continues the turn without the provider). Required controls:

- On every bridge registration, compare the host identity (HEAD plus the 94 hashes) against the applied journal. A mismatch means "host not qualified": refuse patched-mode claims and surface repair. Whether turns also stop is Adrian's policy choice (recommendation 4).
- Record the applied state in the release receipt. Today `release_version.status` checks plugin files only (`release_version.py:65-93`).
- I found no plugin hook that can veto `hermes update`, but I searched only `update_cmd_pause_gate.py`, `update_host_obligation.py`, `update_cmd.py`, `post_update.py`, and `plugins.py`. Treat that as "not found", not "absent".

**Third-party plugins.** The patches change plugin dispatch for every plugin: required middleware semantics, async refusal, and new hook names (`hermes_cli/plugins_policy.py` in the patched tree). I spot-checked one patch: `hermes-strict-inference` keeps provider fallback by default (`allow_provider_fallback=True`). Behavior neutrality of the other nine patches for profiles without the bridge is an untested hypothesis. Qualification would need the stock plugin test suites on the patched tree.

**Shared virtual environment and dependencies.** No Hermes patch changes Hermes dependencies. The bridge's `python_dependencies` install into the shared pm venv through Hermes's plugin installer (`plugins_cmd_install.py:69-160`). Stock `post_update` runs `pm.sync_venv(..., evict_incompatible_plugins=True)` (`post_update.py:281`). That a user venv reproduces the qualified 331-package closure is plausible from the lock diff, but untested.

**Compiled dashboard assets.** The patches do not touch `web/`, so the user's built `web_dist` stays valid. The bridge's own `dashboard/dist` assets are plugin files.

**Restore and removal when later edits exist.** Restore refuses on any after-hash mismatch, so nothing is lost silently. Removal must run provider return first (as `removal_preparation.py:13-14` already requires), then host restore, then plugin removal. A host restore while ownership is enabled must be refused, otherwise memory admission disappears under an owned store.

**Policy behavior during transition.** Every consumer is stopped between the stop and start steps, so no turn runs on mixed code. After start, either the patched host verifies and patched mode registers, or the transaction rolls back to stock files and the bridge reports reduced mode explicitly.

**Full-chain memory ownership and grants.** Keep the current chain unchanged:

- An authenticated dashboard owner.
- A short-lived mount grant bound to the job and action (`release_worker.py:95-100`, `install_source.py:389`), revoked after the worker (`release_worker.py:303-320`, `release_worker.py:453-456`).
- A separate ownership activation.
- Per-client HTTP grants.

A host patch must not enable ownership. Ownership activation should require the verified patched-host state.

**Cancellation.** Pending-question interruption and clarify cancellation come from `hermes-session-lifecycle.patch` (`tools/clarify_gateway.py`, `gateway/run_turn_runner_clarify_delivery.py`, with tests `test_stop_clarify_waiters.py` and `test_clarify_cancellation_outcome.py`). They exist only while the patched host is verified. Operation cancellation (worker death, interrupted preparation) is covered by the journals.

**LifeOS fetch on activation.** `prepare_lifeos` clones the upstream repository and **refuses when upstream HEAD differs from the pin** (`install_source.py:145-151`). That is an obsolete assumption (F9): once upstream moves, a fresh activation fails. It should fetch the exact pinned commit, and fall back to a C-style LifeOS asset if the upstream commit is unavailable. The full clone carries 717 commits (17.7 MB gzip of `.git`). A single-commit fetch is probably smaller, but that is unmeasured, since I used no network.

### 6.2 Option B: reuse the existing upstream base, private derived runtime

Instead of editing the user's checkout, derive the patched tree from the base commit object in the user's local repository:

- `git worktree add --detach` (E8, about 2 s, primary checkout untouched).
- Or `git archive` or a reflink copy (E7).

Then apply the ten patches and require the same tree digest as today's manifest (E1). Build the private runtime as today, from that tree instead of `package/hermes`. `prepare_hermes` already clones a local repository at the pinned commit (`install_source.py:216-250`), although it currently demands a clean source checkout at that HEAD (`install_source.py:222-225`). B only needs the commit object, so that requirement becomes obsolete for this path.

Properties:

- **Local edits are irrelevant.** The derived tree comes from the commit object, not the working tree.
- **Newer user Hermes.** If the user's HEAD is newer and the base exists in history, B would select an older Hermes than the one the user runs. That is a downgrade. It must be an explicit owner decision with the version shown, never automatic.
- **Missing base.** If the base is absent, or a `blob:none` partial clone lacks blobs, fetch exactly that commit (network, unmeasured) or use the C1 stock asset.
- **Worktree caution.** A worktree depends on the user's object store, so a user `git gc --prune` or repository deletion would affect it. For removal and rollback sources, prefer an independent copy: reflink on CoW filesystems, otherwise a full copy of about 214 MB. Removal can also derive stock by reverse-applying the patches (E3).
- **Unchanged guarantees.** Ownership, apply, rollback, removal, and memory chains are unchanged from the qualified design. Only the source of bytes changes.

### 6.3 Option C: split content-addressed component assets

Publish components keyed by content digest:

- A stock Hermes base per commit (81.2 MB, reused while the base is unchanged).
- A LifeOS base or patched worktree per commit (15.9 MB).
- The integration (2.6 MB).
- Qualification tests (0.8 MB, not needed at runtime).
- The dashboard (1.5 MB, already separate).
- Bun by digest.

The certificate binds every component digest and the derived tree digests (`tree_sha256`). The release identity stays one immutable certificate, and component reuse never changes what was qualified. Drop the patched `hermes/` worktree, both `.git` directories, and the per-package `stock-hermes.tgz` copy.

Obsolete assumptions to change:

- Package and candidate validators call `git rev-parse HEAD` (`install_source.py:138`, `install_source.py:209`, reached through `release_stage.py:166-167`).
- `runtime_source_fingerprint` includes `.git` (`release_stage.py:28-29`).
- Hermes derives its version from `.git` for unstamped trees (`version_info.py:1-10`). Without `.git`, Hermes identity and its update behavior change. Write an install stamp, and qualify `hermes --version` and `hermes update` refusal. That this is acceptable is an untested hypothesis.

### 6.4 Option D: unpatched stock Hermes via current plugin APIs

Stock v0.21.7 lacks these hooks: `pre_prompt_admission`, `pre_command_approval`, `augment_tool_result`, `pre_turn_stop`, `on_turn_result`, and `pre_message_delivery`. It also lacks required middleware (stock `plugins.py:109-170`, `middleware.py:17-26`). Not possible without host changes:

- **Lasting-memory ownership.** It is fail-closed by design (`memory_provider.py:99-115`).
- **Prompt blocking before the model request.** `pre_llm_call` can add context, not block.
- **LifeOS Bash permission allow, ask, and replacement decisions, and denial precedence over Hermes approval paths.** Deny-only through a `pre_tool_call` veto may be possible (stock comment at `plugins.py:144-147`); that is a hypothesis.
- **Withholding a rejected answer before delivery and persistence.** Stock `pre_verify` fires only after code edits and is nudge-bounded, so it is not equivalent.
- **Tool-result composition.** Stock `transform_tool_result` replaces results; it does not compose them.
- **Turn-result activity for the watchdog.**
- **Outbound private-audience delivery check.** Stock `pre_gateway_dispatch` is inbound only.
- **Per-child provider, model, and effort.**
- **Selected-provider inference without fallback.**
- **Remote whole-file stale-write protection.**
- **Installation-bound cron bootstrap.**
- **Session start, resume, and clear reasons and pending-question interruption.**
- **Web result status for External Safety.**

The historical reduced-mode table (`docs/history/2026-10-16-installation-workflow.md`) lists the same set. D is valid only as an explicit "reduced, memory ownership unavailable" outcome.

### 6.5 Option E: upstream changes and runtime alternatives

**Upstream.** The patched hooks are mostly generic extension points: required synchronous middleware, a fail action for the stop gate, outbound delivery checks, per-child routing kwargs, and a provider-fallback flag. Upstreaming them is the only path to "plugin only, any recent Hermes". It depends on maintainers; no engineering result here proves acceptance.

**Runtime monkeypatch at `register()`.** Not viable for most of the delta. `hermes_cli.plugins` is already imported when it loads the plugin, and call sites in turn code need new invocations, not attribute swaps.

**Import overlay.** A `.pth` file in the venv could install a `sys.meta_path` finder that serves hash-checked patched copies of the 58 runtime modules before Hermes imports them. Every property of this is untested:

- startup ordering;
- survival of pm `sync_venv`;
- sealed or Nix stores;
- bytecode caches;
- tracebacks and tools that read source by path;
- every profile sharing the venv.

It would leave the checkout clean, so `hermes update` would not stash it. It would then run the overlay against new upstream modules, and its hash check would have to refuse them. A bounded probe is required before it is considered.

**Sidecar process.** It cannot intercept in-process admission or delivery. Not viable for the safety contract.

## 7. Compatibility matrix

Outcomes for each Hermes layout. "Refuse" always means no file change and an explicit owner-visible reason.

| Layout | A in place | B local base | C split assets | D stock plugin |
|---|---|---|---|---|
| Default Git checkout, HEAD = base, clean | Supported (restricted proof) | Supported | Supported | Reduced |
| Same, local edits or untracked files | Refuse (list paths) | Supported (ignores the working tree) | Supported | Reduced |
| Git, HEAD newer, base in history | Refuse (would require a downgrade) | Owner-confirmed downgrade only | Owner-confirmed downgrade only | Reduced if the hooks exist |
| Git, base absent or missing blobs | Refuse | Fetch the exact commit or fall back to C | Supported | Reduced |
| ZIP install, no `.git` | Refuse (untested) | Use the C asset | Supported | Reduced |
| pip or pipx site-packages | Refuse (unknown layout) | Use the C asset | Supported | Reduced |
| Docker, Nix, desktop-app stamped | Refuse (steward-owned) | Out of scope: the current systemd user service prerequisite fails | Same | Reduced |
| Root-owned or multi-account install | Refuse (no escalation) | Private runtime for this account only | Same | Reduced |
| Multiple profiles share the checkout | Refuse in the first proof | Current account-wide launcher model; removal refuses | Same | Reduced |
| Already patched, our journal | Idempotent "applied" | n/a (private tree) | n/a | n/a |
| Already patched, no journal | Refuse or owner-reviewed adopt | n/a | n/a | n/a |
| Unknown Hermes version | Refuse | Refuse, or owner-confirmed switch to the qualified base | Same as B | Reduced, with the actual hook set reported |

## 8. Defined outcome for unknown versions

Recommended rule. It is a proposal; Adrian decides it.

1. The host identity is classified as `qualified-base`, `qualified-patched`, `newer`, `older`, `unknown`, or `sealed`.
2. Only `qualified-base` and `qualified-patched` allow patched-mode activation.
3. `newer`, `older`, and `unknown` show three choices: stay unchanged (D, reduced, memory ownership unavailable), switch to the qualified private runtime (B or C, an explicit version change), or wait for a qualified release.
4. `sealed` allows D or nothing.
5. No path changes the selected Hermes version without that explicit choice.

## 9. Reusable code and obsolete assumptions

**Reusable as is or with small changes:**

- `ProgramTransaction`: journaled file and directory publication with later-edit refusal and retained before-copies (`release_programs.py:97-400`).
- `publish` and `fingerprint` (`release_programs.py:25-94`).
- `_tree_digest`, `validate_hermes_candidate`, and `validate_candidate`, with the Git checks removed (`install_source.py:103-142`, `install_source.py:195-213`).
- `prepare_hermes`, which clones a local repo at the pin (`install_source.py:216-250`), for B.
- `stage_hermes_patch`, `apply_hermes_patch`, `restore_hermes_patch`, and `recover_hermes_patch` state logic (`install_source.py:468-673`), for A, rebuilt on `ProgramTransaction`.
- `stock_hermes.build_archive`, `prepare_source`, and `validate_archive` (`stock_hermes.py:28-106`), for C's stock asset.
- `ReleaseCatalog` asset verification (`release_catalog.py:107-142`).
- Service drain and quiesce (`release_worker.py:392-402`) and process inventory (`removal_consumers.py`), for A's all-consumer stop.
- The installation and program locks (`release_worker.py:327-330`).
- The memory grant chain (`release_worker.py:95-100`, `release_worker.py:303-320`).

**Obsolete under the proposal:**

- Validators that require `.git` (F8).
- `prepare_lifeos` requiring upstream HEAD to equal the pin (F9).
- `prepare_hermes` requiring a clean source working tree when only the commit object is needed (`install_source.py:222-225`).
- A full archive download for every preparation, and Bun downloaded per job (F12).
- `stock-hermes.tgz` inside every package (C replaces it with one reusable asset).
- The silent reduced-mode registration (F5).
- The host-patch worker binding to one gateway unit (`install_source.py:730-737`).

## 10. Affected modules and tests

| Change | Modules | Tests to extend or add |
|---|---|---|
| C1 split assets | `scripts/build_managed_release.py`, `release_catalog.py`, `release_stage.py`, `install_source.py`, certificate format, `stock_hermes.py` | `test_release_catalog.py`, `test_release_stage.py`, `test_stock_hermes.py`, `test_latest_hermes.py`, `test_lifeos_install_source.py`, plus a new derived-tree equality test against the 0.7.3 manifests |
| C2 caching and retention | `release_tools.py`, `release_stage.py`, `cli.py` | `test_release_preparation.py`, new cache tests |
| B local base | `install_source.py`, `release_stage.py`, `cli.py` | New worktree, partial-clone, and downgrade-refusal tests, plus `test_release_stage.py` |
| D explicit | `lifeos_hook_bridge/__init__.py`, `release_version.py`, `plugin_api.py` `/installation` | `test_bridge.py`, `test_dashboard_api.py`, stock and patched registration fixtures |
| A in place | `install_source.py` (rebuild on `ProgramTransaction`), `plugin_api.py:1328-1425`, `release_version.py`, `profile_services`, `removal_*` ordering | `test_hermes_install_source.py`, `test_release_programs.py`, `test_dashboard_api.py`, new real-service tests in an isolated account (no stubbed stop and start) |

## 11. Staged implementation and qualification plan

All stages ship as one release package, per the release policy. The stages give dependency order and verification gates, not separately deployed pieces.

1. **Derivation proof (offline).** For the 0.7.3 bases, derive the Hermes and LifeOS trees from stock plus patches. Assert equality with `hermes-source-manifest.json` and `lifeos-source-manifest.json` `tree_sha256`. Hermes is already shown in E1; LifeOS is still to do, because I did not run it. Gate: exact digest equality.
2. **Split certificate format and builder.** Emit component assets and a certificate binding their digests and the derived digests. Gate: building twice from the same commit yields identical digests, and a certificate change is detected.
3. **Validators without Git, plus an install stamp.** Gate: the qualified runtime reports the same version identity. `hermes update` refuses or behaves as specified on the stamped runtime. This must be tested, because it is not known today.
4. **Catalog reuse and retention.** Gate: a second preparation with the same bases downloads only the integration asset. Superseded operations are pruned only after rollback windows expire.
5. **B local-base derivation.** Gate: the derived tree digest equals stage 1. Cases: clean, dirty, newer HEAD (refuse without owner confirmation), partial clone, missing commit (fallback).
6. **Explicit host-state reporting (D-explicit).** Gate: stock, patched, and drifted hosts each report the correct state. Memory ownership stays fail-closed. Reduced mode is never silent.
7. **Exact-archive qualification of the new package**, with the full release gates in `docs/update-policy.md:41-52`: fresh install, update, interruption recovery, rollback, removal, memory ownership, and HTTP grants in isolated accounts.
8. **Optional A-restricted proof.** Only after stages 1 to 7, in an isolated account with real systemd units, real CLI sessions, and two profiles. Gates: all-consumer stop; capability probe in the new processes; crash injection at every journal state; `hermes update` with adjacent, unrelated, and overlapping upstream commits; restore with later edits; third-party plugin suites on the patched tree.

## 12. Measured facts versus hypotheses

**Measured here:**

- Archive identity.
- Component sizes, uncompressed and gzip.
- The three Hermes base copies.
- The 94-file delta.
- Patch stats.
- The lock difference.
- E1 to E9.
- The existing test results.

**Read in code, not executed:**

- The current download, runtime, launcher, removal, memory fail-closed, and silent reduced-mode paths.
- Hermes stash and reset behavior.
- The update lock.
- Memory-provider-unavailable behavior.
- The install layouts.

**Untested hypotheses:**

- User venv closure equivalence.
- Update-lock exclusion.
- Behavior neutrality of the other nine patches.
- Single-commit fetch sizes.
- The import overlay.
- Hermes identity and update behavior without `.git`.
- The 1.08 GB per-operation disk estimate.
- Bun, wheel, and native package transfer per preparation.
- The LifeOS derivation equality from stage 1.
- Actual `hermes update` behavior on today's managed runtime, which has `.git` with a builder-local origin.

No network or service behavior was measured.

## 13. Items for Adrian's review

- **Riskiest claim.** The B + C transfer estimates are sums of independently compressed components, not built assets. Expect a few percent of difference.
- **Decision I made.** I ranked in-place patching (A) last among the implementable options, on compatibility and blast-radius grounds, not effort. The deciding evidence is the Git-level E9 simulation plus code reading of the Hermes updater, not a run of `hermes update`.
- **Decision needed: drift policy.** When a profile expects a patched host but finds stock or drifted code, should turns fail closed or only warn? Today memory fails closed and policy silently degrades.
- **Decision needed: downgrades.** May B or C ever select a qualified base older than the user's running Hermes, with owner confirmation? The proposal assumes yes, never automatically.
- **Existing gap, independent of this proposal.** The managed runtime ships `.git` whose `origin` is a builder-local path, and nothing blocks `hermes update` on it. That deserves its own test.
- **Not covered by these tests:** real wheels, ZIP installs, Docker or Nix, multiple profiles, third-party plugins, and any network fetch.
- **Changes outside Git:** only the disposable directory `/home/outsider/.cache/minimal-install-review-20261016` (4.8 GB apparent size by `du -sh`, some of it reflink-shared; safe to delete with `rm -rf`). The archive and qualification fixture were not modified. The parent's `primary-*`, `prompt.txt`, `result.json`, `pid`, `launcher.*`, and `stderr.txt` files in this directory were not read or modified.
