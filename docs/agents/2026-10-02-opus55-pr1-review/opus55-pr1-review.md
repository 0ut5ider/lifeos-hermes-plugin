# PR #1 review: governed LifeOS memory integration

- Date: 2026-10-02
- Role: independent code reviewer (correctness, security, data preservation, test coverage). Review only; no implementation, test, configuration, or Git changes.
- Question: Does the executable change from base to head contain reachable failures or release blockers in authorization, memory confidentiality, installation/update/restore recovery, detached execution, or test coverage?
- Requested model: claude-opus-5-5, effort medium. Actual model: Opus 5.5 (claude-opus-5-5), effort medium.
- PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/1 (draft)
- Base: `648fe30a5c5f40551c9a3d73f0d80f527dbd7412`
- Head: `4190e9929f90f058622ce6d9cc4d64444fbbb508`

## Summary

I found two confirmed correctness findings that matter for release, one confirmed low-severity finding in the private recorder, and one low static finding. Both main findings are reproduced with real temporary files or a real local process.

1. **F1 (High, reproduced):** the new browser `Restore previous LifeOS version` path deletes later edits to the Hermes profile `config.yaml`, `.env`, `SOUL.md`, and `plugins/lifeos/`. The user-data guard does not check these files, and the deleted versions are not archived anywhere.
2. **F2 (Medium, dormant, reproduced):** direct child inference (`claude_direct.py`, local gateway path) runs memory admission on `{'model': ...}` only. A forgotten claim in the child system prompt or user content reaches the model endpoint. The same check refuses that content when it receives the full body.

The bounded gate passes (337 tests, no skips or warnings). The tests do not cover either defect.

## Confirmed findings (severity order)

### F1. Browser version restore deletes later Hermes profile edits without a guard or archive

- Severity: High (data loss on a new authenticated browser path). Status: reproduced.
- Files: `lifeos_hook_bridge/update_transaction.py:68-87` (`_restore_mount`, unlink at line 77, `rmtree` at line 75), `lifeos_hook_bridge/update_transaction.py:188-198` (`validate_restore` checks only `_memory_digest` of the LifeOS tree), `lifeos_hook_bridge/dashboard/plugin_api.py:605-648` (new restore route).
- Caller path: browser `POST /api/plugins/lifeos-hook-bridge/installation/update/restore` → `_resume_lifeos_update(..., 'restore')` → `validate_restore` → detached `update_worker.py --action restore` → `restore_update` → `_restore_mount`.
- Failure: after an update reaches `applied`, the owner changes `~/.hermes/config.yaml` (for example a model choice) or adds a provider key to `~/.hermes/.env`. Restore passes the guard because those files are outside `LIFEOS/MEMORY`, `LIFEOS/USER`, `USER.md`, and `MEMORY.md`. `_restore_mount` then unlinks each mount target and copies the pre-update snapshot. A target that was absent before the update (here `.env`) is deleted. Nothing is moved into the snapshot first, so the later content is unrecoverable. The program tree gets moved to `restored-selected`, but the profile files do not.
- Additional violated invariant (beyond the documented open "successful restore preserving later audit data" item): the PR applies "recovery does not overwrite a later edit" to mount recovery (`mount_transaction.py:209-216`, `docs/verification/2026-10-02-mount-acceptance/README.md` line 11). Restore writes the same eight profile targets with no such check, and the route's guard text ("refuses restoration when user data has changed") does not cover them.
- Reproduction: `PYTHONDONTWRITEBYTECODE=1 python docs/agents/2026-10-02-opus55-pr1-review/raw/repro_update_data.py` (uses the repository `UpdateTransactionTests` fixture). Output in `raw/repro_update_data.txt`, key `R2_restore_profile_edit`.
- Expected: restore refuses (409) when the current profile targets differ from the digests recorded after the update, or it preserves or archives them. Actual: `route_guard: passed`, `config_after_restore: "prior config"`, `env_exists_after_restore: false`, `later_edit_copies_retained_anywhere_in_snapshot: []`.
- Suggested correction: record digests and modes of the mount targets (and the `plugins/lifeos` file set) in the manifest when the update reaches `applied`. Have `validate_restore` compare them and refuse on difference, the same way `MountTransaction._checks` does. If the policy should allow restore after profile edits, archive the current targets in the snapshot before replacing them. Add a regression test that edits `config.yaml` and `.env` after `applied` and expects refusal with unchanged bytes.
- Reachability limit: the strict LifeOS user-data guard currently refuses most live restores because a native hook appends `OBSERVABILITY/config-changes.jsonl` (documented). Any restore that passes the guard reaches this deletion. Relaxing the guard to close the documented open item makes it more reachable.

### F2. Direct child inference skips retired-claim checks on the content it sends

- Severity: Medium. It is dormant on live installs because ownership is disabled, but it blocks activation. Status: reproduced.
- File: `lifeos_hook_bridge/bin/claude_direct.py:147-158`.
- Caller path: native `Inference.ts` → `bin/claude` shim with `LIFEOS_CHILD_INFERENCE_DIRECT=1` and no `LIFEOS_CHILD_PROVIDER` → `claude_direct.main` → `MemoryRuntime.check_call(request={'model': args.model}, ...)` → `urllib` POST to `ANTHROPIC_BASE_URL`.
- Failure: `check_call` gets a body with no `system` and no `messages`, so `_system_text`, `retained_messages`, and `project_request` have nothing to check. The real `request_body` (lines 152-158) carries the child system prompt and user content to the model unchecked. The provider path (`_run_hermes_provider`) goes through Hermes `call_llm` and its required middleware; this path does not.
- Additional violated invariant: the runtime enforces "removed or superseded claims never reach a model input" for primary, auxiliary, compression, and review calls (`memory_runtime.py:304-325`). This route runs the admission call but makes it ineffective for content. That is a defect in implemented code, not only the open "complete child route coverage" item. `tests/test_memory_children.py` covers route approval and invalidated context only, so it passes.
- Reproduction: `PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE LIFEOS_MEMORY_SOURCE=<fixture>/lifeos/LifeOS/install python docs/agents/2026-10-02-opus55-pr1-review/raw/repro_child_direct.py`. Output in `raw/repro_child_direct.txt`.
- Expected: child exits non-zero and the gateway receives zero requests (the control check with the full body refuses: "The model system prompt contains a removed or superseded claim"). Actual: `child_exit_code: 0`, `requests_received_by_gateway: 1`, `forgotten_claim_in_sent_system_prompt: true`.
- Suggested correction: build `request_body` first, then call `check_call(request=request_body, ...)` (with `project=True` semantics if history projection is intended) and send the checked body. Add a regression next to `test_actual_gateway_checks_approved_route_and_invalidated_memory` that forgets a fact, admits a fresh session, and sends the forgotten text as the child system prompt and as user content.

### F3. Private recorder keeps credential values whose environment names do not match its name pattern

- Severity: Low (development-only recorder, private 0700 store, outside the release package). Status: reproduced at function level. Whether these exact names appear on the acceptance host is a hypothesis.
- Files: `development/hook_capture/store.py:22` (`SENSITIVE`), `development/hook_capture/instrument.py:602` (records `options: kwargs`, which includes the complete hook `env` copied from `os.environ` at `bridge.py:1298-1301`).
- Failure: names such as `ANTHROPIC_KEY`, `GH_PAT`, `SSH_PASSPHRASE`, and webhook URLs that carry the secret in the path (`SLACK_WEBHOOK_URL`) survive `safe()`. `*_API_KEY`, `*_TOKEN`, URL user information, and sensitive query parameters are redacted.
- Reproduction: `python docs/agents/2026-10-02-opus55-pr1-review/raw/repro_recorder_redaction.py` → `raw/repro_recorder_redaction.txt` (four of seven synthetic values `RETAINED`).
- Suggested correction: do not record the hook `env` mapping at all, or record only names plus a fixed allowlist of non-secret values. The README already admits unknown credentials can survive. An environment allowlist removes the largest source.

### F4. Every mount keeps permanent private copies of `.env` and `config.yaml`

- Severity: Low (credential retention). Status: static analysis.
- File: `lifeos_hook_bridge/mount_transaction.py:301-330`. `execute` writes `snapshot/stage/.env`, `snapshot/previous/<n>`, and `snapshot/selected/<n>` under `<profile>/.lifeos-mount/<uuid>/`, and no code removes committed or rolled-back snapshots.
- Failure: each finalize, remount, and update leaves another 0600 copy of the provider credentials. A key the owner rotates or deletes from `.env` stays on disk indefinitely, and the copies grow with each mount. The previous finalize code also left a `mount-snapshot-*` directory, so this pattern predates the PR. The PR makes it per-remount and reachable from PULSE.
- Suggested correction: after `committed` or `rolled_back`, remove snapshot directories other than the one the current journal references. Keep the journal-referenced snapshot only while recovery can need it.

## Hypotheses (not reproduced)

- **H1. Concurrent restore or recover requests can launch two workers.** `_resume_lifeos_update` (`plugin_api.py:614-648`) has no job lock. Two near-simultaneous owner requests both see `applied`, both rewrite `request.json`, and both launch units. In the race, the second worker can run `stop()` and then fail on `os.replace` onto a non-empty `restored-selected`. That leaves the gateway stopped and the manifest saying `restoring`. The apply route has the same pre-existing gap. To test it, run two restore launches against one job with a barrier inside `validate_restore`.
- **H2. The apply grant can expire during a long update.** `plugin_api.py:575` issues a 3600-second grant before the worker does the full copy, dependency sync, and reference install. If those take longer than an hour, `MountTransaction.execute` refuses after the swap and the update rolls back. This fails closed, but the cause is not reported. I did not measure update duration.
- **H3 (pre-existing, not introduced).** `apply_update` copies the installed tree and swaps it while only the gateway is stopped (`update_transaction.py:143-149`). In a layout where `LIFEOS/MEMORY` is a real directory, a write by another service during the copy lands only in `snapshot/live-prior` (`raw/repro_update_data.txt`, `R1_concurrent_write`). Managed memory requires `LIFEOS/USER` and `LIFEOS/MEMORY` to be symlinks into `~/.config/LIFEOS/USER` (`memory_access.py:65-72`), so governed writes are not lost this way. I classify this as pre-existing behavior for unmanaged layouts.

## Already documented limitations (not counted as new findings)

- Successful browser restore preserving later native audit data; strict guard refusal (documented in PR and acceptance README).
- Remaining native readers and derivatives, restricted prompts and delivery, retained-session reconstruction, child/compression/resume coverage (F2 is reported only because implemented code makes its own check ineffective).
- Ownership activation, source-review page controls, schema 4 rollback incompatibility, established-profile trial/import/removal, full release gate.
- Same-operating-system-identity processes can forge `LIFEOS_MEMORY_CONTEXT`, read the grant key, or replace files between attestation and read (documented in the plan).
- A copied stateless bearer is not revoked by logout; binding removal denies it (documented).

## Optional improvements (after correctness review)

- `POST /installation/update` and `POST /installation/update/recover` do not apply `_fixed_mount_request` (Origin and empty-body checks) like restore, remount, and mount recovery do (`plugin_api.py:548, 595`). The Hermes `SameSite=Lax` session cookies block cross-site POSTs, so I report this as a consistency hardening, not a finding.
- `MemoryService.administrative` validates grants without `check_binding` (`memory_service.py:219`). A job-bound apply or restore grant can therefore authorize prompt preview and publication through `memory_rpc.py` while it is valid. Only same-user processes can do this, and the operations are limited to prompt mounting. Binding the administrative path to the mount job, or to `purpose='mount'` with no job binding, would narrow it.
- `run_update_job` does not revoke the grant when its initial `mount_environment` validation raises (`update_worker.py:227-229`). Expired grant files then accumulate in `.lifeos-memory-admin/`.

## Coverage of changed executable components

| Component | Status | Notes |
| --- | --- | --- |
| `memory_administration.py` | Reviewed, tested (gate) | Grant issue/validate/revoke, binding, purpose, connector check. |
| `mount_transaction.py` | Reviewed, tested (gate) | Journal, checks, restore, mode handling. F4. |
| `update_worker.py`, `update_transaction.py` (diff) | Reviewed, tested, reproduced | F1, H2, H3. |
| `dashboard/plugin_api.py` (memory and installation routes) | Reviewed, tested (gate) | F1 route, H1, optional Origin note. |
| `install_source.py` (finalize diff) | Reviewed, tested (gate) | Finalize through MountTransaction. |
| `version_drift.py` (diff) | Reviewed | Two plugin files tracked. |
| `memory_http.py`, native relay in `lifeos-memory-access.patch` (MemoryAccess.ts, PULSE memory/hermes routes, Mount.ts) | Reviewed (relay, origin, remount, staged mount), tested (gate) | Wiki/Knowledge/Cortex/Observability native renderers only skimmed. |
| `memory_service.py`, `memory_policy.py`, `memory_context.py`, `memory_rpc.py` | Reviewed, tested (gate) | Identity resolution and context parsing. |
| `memory_runtime.py`, `memory_provider.py`, `__init__.py`, `bridge.py` (diff) | Reviewed, tested (gate) | Dormant while ownership is disabled. |
| `bin/claude`, `bin/claude_direct.py` | Reviewed, reproduced | F2. |
| `memory_sharing.py`, `memory_mcp.py`, `memory_preferences.py` | Reviewed, tested (gate) | Owner checks, SSH forced command, revocation. |
| `hermes-required-middleware.patch` | Reviewed (additions) | Required-failure propagation. Its pytest suite was not run. |
| Other Hermes patch diffs (8 files, small) | Not reviewed | Only diff sizes inspected. |
| `memory_access.py` | Partially reviewed (boundary, connection, schema, `_allowed`) | Write, correct, forget, adoption, and proposal internals not reviewed line by line. |
| `memory_restore.py`, `memory_staging.py`, `memory_sources.py`, `memory_source_review.py`, `memory_diagnostics.py`, `memory_canonical.py`, `memory_wiki.py`, `memory_knowledge.py`, `memory_pulse.py`, `memory_prompt.py`, `memory_proposals.py`, `memory_adoption.py`, `memory_history.py`, `memory_native.ts`, `memory_publication.ts`, `memory_transaction.py` | Authorization entry points spot-checked; tested where in gate | Internal filtering logic not independently re-reviewed. Earlier archived reviews cover them. |
| `development/hook_capture/*` | Partially reviewed (subprocess/HTTP capture, redaction), tested (30 pass) | F3. Analysis and bootstrap not reviewed. |
| `scripts/prepare_sources.py`, `scripts/rebuild_hermes_patches.py`, `development/probes/remote_capture.py` | Not reviewed | `test_prepare_sources` passes in the gate. |
| `dashboard/dist/index.js` | Not reviewed (UI tests pass) | 11 node tests. |

## Commands, results, and limits

See `raw/commands.txt` for exact commands.

- Bounded gate (31 modules, `-W error::ResourceWarning`): 337 tests pass in 240.280 s, exit 0, no skips, no warnings (`raw/gate.txt`). Fixture patch hashes match HEAD for all 19 patches.
- Development recorder: 30 pass (`raw/development-tests.txt`).
- Dashboard UI: 11 pass (`raw/dashboard-ui.txt`).
- `test_memory_children` and `test_update_transaction`: 6 run, 5 pass, 1 skipped in my ad hoc run because I did not set `LIFEOS_TASK_HOOK_PATH`. The skipped case ran and passed in the gate.
- Three reproduction scripts with outputs in `raw/`.
- I did not run the complete 600-case memory regression, the Hermes pytest suite added by the patches, live systemd, browser, SSH remote, Docker, or real-model tests. I did not rerun any archived historical test.
- The passing tests show only that the covered contracts hold. They cannot show restore preservation of profile edits (F1), content checks on direct child inference (F2), live systemd behavior, concurrency between routes (H1), or real update durations (H2).

## Merge recommendation

Do not merge as a release candidate. Keeping it as a draft is appropriate. Reasons:

1. F1 is a reachable data-loss path on a control this PR adds. Restore needs a guard or archive for profile mount targets before it ships, independent of the documented audit-data open item.
2. F2 must be fixed before any ownership activation, because it defeats the retired-claim invariant on an implemented model-call route.
3. Both fixes are local: F1 touches `update_transaction.py` plus one test, and F2 touches `claude_direct.py` plus one test. The rest of the reviewed authorization, grant, and mount-journal design held up under review and the bounded gate.

This review does not establish full hook parity, full memory acceptance, or release acceptance.
