# rc2 fixes review, round 2

- Date: 2026-10-18
- Role: code reviewer
- Model: Opus 5.5 (claude-opus-5-5)
- Question: Review commit 300e9d40 on `feature/minimal-install-review`. The commit replaces the round 1 file parser
  (`basic_settings`) with a login that the dashboard process takes from the running Hermes basic provider, records
  in the private workflow request and the signed removal plan, and uses for standalone recovery. Check security,
  the request schema change, coupling to Hermes private attributes, the round 1 notes, tests, docs, and standards.

Raw data is in `raw-round2/`: test outputs `rv3-a.txt` to `rv3-f.txt`, and two probes with their output.

## Tests

All requested modules pass in the frozen environment:

| File | Module | Result |
|---|---|---|
| rv3-a.txt | test_removal_recovery | 3 OK |
| rv3-b.txt | test_portability_dashboard | 6 OK |
| rv3-c.txt | test_memory_removal_workflow | 5 OK |
| rv3-d.txt | test_release_dashboard | 8 OK (1 skipped) |
| rv3-e.txt | test_removal_p* | 13 OK |
| rv3-f.txt | test_removal_s* | 9 OK |

Probes (real fixtures, only prompts and launch patched):

- `probe_rc1_plan.py`: `removal_recovery.main()` on a retained plan without `recovery_login` exits 1 with the
  generic refusal and launches nothing. `recovery_login(None, owner)` raises `ReleaseRejected`. Fails closed.
- `probe_queue_login.py`: `queue` for a removal without a login raises `ReleaseRejected` and leaves no job. With
  `dashboard_login('dashboard:basic:owner')`, the job directory is 0700, `request.json` is 0600, the request holds
  exactly `username` and `password_hash`, and `workflow_job` accepts it.

## 1. Security

- New authority: none found. Standalone recovery still needs a shell as the account plus the dashboard password.
  The recorded hash comes from the provider that verifies that password, and `dashboard_login` requires
  `account == 'dashboard:basic:' + provider._username`, so a session from another provider or an old username gets
  403. A same-account attacker could rewrite `plan.json` and the marker, but that account could already rewrite
  `config.yaml` in rc.1.
- Hash exposure: acceptable. `request.json` and `plan.json` are written through `release_programs.publish` with
  mode 0600 (fchmod before write, atomic replace) in 0700 job directories, and `read_private` refuses a non-owner or
  group/other-readable file. The hash is the same value that normally sits in the 0600 `config.yaml`. In the
  plaintext-environment case, Hermes hashes in memory with a fresh salt, so the plaintext never goes to disk.
  `status()` returns `status.json`, `review.json` (the prepare return dict, which has no plan or login), and the
  receipt. Neither the HTTP API nor the UI receives the login.
- Signature coverage: `recovery_login` is a key of `plan`. `signature = sha256(_encoded(plan))`, and
  `removal_state.prepared` recomputes the hash over the whole `plan.json`. The login in `request.json` is also
  covered by the admission binding (`request` sha256 in `binding`) and by the preparation-review signature.
- Validation at every read for authentication: there is one authentication read, `removal_recovery.main`, and it
  calls `recovery_login(plan.get('recovery_login'), plan['owner'])` before `authenticate`. `queue` and `prepare`
  also validate it.
- rc.1 plans: fail closed in the new code (probe above). In practice, the saved `recover` command runs the retained
  `recovery-manager/removal_recovery.py` copy from the job (`removal_bootstrap.py:62`), so a removal that rc.1
  prepared keeps using rc.1's config.yaml path. The new code reads an rc.1 plan only in the unusual case where the
  retained copy is new.

## 2. Request schema and ordering

- `workflow_job` adds `login` to the allowed key set only when the request already has `login` and the selection
  kind is `removal`. A `login` on any other kind fails the exact key-set check. The value itself is not validated
  here, but `prepare` validates it again, and status/recovery never use it. Correct.
- `queue`: a non-removal kind with a login refuses first (cheap, before any lock). For a removal, the pending
  workflow refusal (`RuntimeError`) comes before `recovery_login`. The existing test
  `test_other_owner_and_other_workflow_cannot_use_retained_removal_authority` calls `queue` without a login and
  expects `RuntimeError`, so it confirms this order.
- `execute` passes `request.get('login')` only in the `removal` branch, and `removal_workflow.execute` forwards it
  only to `prepare`. Correct.

## 3. Coupling to Hermes private attributes

- If `_username` or `_password_hash` disappear or change type, `getattr(..., None)` gives a non-string and
  `dashboard_login` raises 403 with "Complete removal requires the password-authenticated dashboard owner". Safe.
  The message does not say that the cause may be a Hermes change (non-blocking 1).
- If `hermes_cli.dashboard_auth.registry` moves, the import raises `ImportError` inside the async handler. That is
  a 500, not a 403. It fails closed and only for removal (non-blocking 1).
- Scope: in Hermes v0.21.7, `PluginContext.register_dashboard_auth_provider` (`hermes_cli/plugins.py`) only calls
  `register_global_provider`, and it refuses a registration from any manager whose scope is not the launch scope.
  The gate (`middleware.py`, `request_utils.py`) uses `list_session_providers()` and `get_provider('basic')` uses
  `_merged(None)`, so both read the same global map plus the same (empty for dashboard auth) overlay. I found no
  Hermes code that registers a scoped dashboard-auth provider. No divergence scenario.
- Rotation: `register_global_provider` upserts on re-discovery after a password change. A session that survives
  the rotation (stable secret) gets the new hash, which is the current password. A changed username gives 403.

## 4. Round 1 findings

- B1, B2, B3: resolved by removal of the parser. Nothing reads `.env`, unit environments, or `config.yaml` for the
  login now.
- Notes 1 to 5 (parity gaps, non-private `.env`, `_private_bytes`, missing user bus, no real `systemctl show` test):
  no longer apply. The provider holds the result of Hermes's own resolution, including managed scope, secret
  sources, and `${VAR}` expansion.
- The "Removal preparation caller" suggestion (validate the hash shape): done with `SCRYPT_HASH`.
- Notes 6 to 11 concern other commits and are unchanged.

## 5. Tests and docs

- The tests listed are correct for what they check. Gaps (non-blocking 2):
  - No test calls the HTTP POST for a removal and checks that `dashboard_login` feeds `queue`.
  - No unit test reaches `recovery_login` inside `removal_preparation.prepare` or checks that `plan.json` contains
    `recovery_login`. The only removal `prepare` unit test stops at the Discord check.
  - No test covers `main()` with a plan that lacks `recovery_login` (my probe covers it).
- The e2e driver now reads the login from the test host `config.yaml` and passes it to `queue`. That matches the
  provider on that host, but it bypasses `dashboard_login`, so the live e2e does not exercise the provider read
  either. I did not find a rerun of the e2e after this commit.
- CHANGELOG and `docs/memory-portability.md`: accurate. The docs line states that a later password change does not
  apply to recovery. That is the real tradeoff: an old password stays valid for this removal's standalone recovery
  (non-blocking 3).

## 6. Standards

- ABOUTME headers are present and updated in `tests/test_removal_recovery.py`. No em dashes in added lines. The one
  new code comment in `workflow_job` explains the current rule, not history. Names are clear.
- `plugin_api.memory_workflows` also changes the claim message condition to consider `.lifeos-removal.json`. That
  is sensible but the commit message does not mention it (non-blocking 4).
- Old verification scripts under `docs/verification/2026-10-15-memory-portability/` call
  `authenticate(profile, ...)`, the old signature. They are dated records, so this is acceptable.

## Non-blocking findings

1. `dashboard_login`: an `ImportError` of the registry gives 500. The 403 text does not separate "not the password
   owner" from "this Hermes does not expose the provider login". A message that names the Hermes version
   dependency would help support.
2. Test gaps listed in section 5, mainly that `plan.json` records `recovery_login` and the HTTP removal path.
3. Password rotation after preparation: the old password remains the recovery password for that removal. It needs
   a shell as the account to use, so it gives no new authority. The docs state it.
4. The status-message change in `memory_workflows` is outside the commit message.
5. `SCRYPT_HASH` refuses a hash with URL-safe base64 characters, which Hermes's non-validating `b64decode` would
   still verify. Hermes's own `hash_password` never produces one. Fails closed.

## Blocking findings

None.

VERDICT: CLEAN
