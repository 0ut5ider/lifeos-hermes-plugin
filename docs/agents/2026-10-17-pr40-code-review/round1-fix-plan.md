# PR 40 review round 1: fix plan

Date: 2026-10-17. Author: Cerebo (primary agent). Inputs: `pr40-spec-review.md`, `pr40-standards-review.md`.

The owner (Adrian) asked to fix all findings and repeat the review until the reviewers come back clean.

## Decisions on findings

| Finding | Decision |
| --- | --- |
| Spec A1, Standards 4 | Implement: unit tests for `inplace_plan.py`, `inplace_worker.py` (`_run` paths, `_rollback`, `verify_registration`, `clear_bytecode`, `inventory_snapshot`, `_consumers_stopped`), `cli._preparation_error`, `scripts/build_integration_release.py` |
| Spec A2 | Implement: fresh-process capability probe after restart (patched hooks in `VALID_HOOKS`, `REQUIRED_MIDDLEWARE_API_VERSION == 1`), and a new main PID with a start time after publication for each restarted unit |
| Spec A3 | Implement: record each bound unit's enabled state (`UnitFileState`) at preparation, in the in-place plan, not in the `ProfileServices` journal (its schema is strict and shared with installed bridges); verify after restart that it is unchanged |
| Spec A4 | Implement in `hermes lifeos-version`: compare the host with `lifeos-host.json` and report drift. Registration only writes the receipt; amend design section 9 accordingly |
| Spec A5 | Implement: the review lists the host files (modified and added), the configuration keys that LifeOS changes, and, for an update, the files that change relative to the installed record |
| Spec A6 | Implement: an optional `known_conflicts` list per manifest entry; the review shows it |
| Spec A7 | Implement: the manifest entry declares the interpreter (`python` major.minor) and the capabilities (hooks, middleware API version); preparation checks the interpreter and runs the capability probe against the preview |
| Spec A8 | Implement: verify memory authority after restart (the memory provider selection is unchanged unless the operation owns the change); amend design section 8 to describe `check_preserved` as the inventory for toolsets, MCP servers, model, and providers |
| Spec A9 | Accept: single-profile admission is the first supported layout; record it in the design |
| Spec A10 | Open: needs a published prerelease and the owner's approval; already recorded |
| Spec B1 | Keep the code; document the workspace-launcher repoint and its trap (review R2-1) in design section 10; the owner decision on R2-1 is still open |
| Spec B2 to B4 | No change; in-scope fixes |
| Spec C1 | Fix: removal tolerates a missing update hold |
| Spec C2 | Fix: check compatibility before the download |
| Spec C3, C4, C6 | Amend the design text to match the code (preview lifetime, no `patches` field in `INTEGRATION.json`, configuration record location) |
| Spec C5 | Fix: a malformed host record yields a specific `host_drift` reason |
| Spec C7 | Verified: `pm.client.sync_venv` defaults to `evict_incompatible_plugins=False`; `dependency_plan` must not pass `True` |
| Standards 1 | Fix the docstring. Keep `_prepare_managed_package`: design section 11 keeps the managed-runtime code until development and daily complete the transition; deletion needs owner approval then |
| Standards 2, 3 | Fix `CONTRIBUTING.md` and `docs/codebase.md` (patch-copy text, new modules, integration release builder) |
| Standards 5 | Fix the `active` guard for `checkCompatibility` |
| Standards 6 | Fix the `argparse` descriptions |
| Smells | Fix: `programs._load()` callers get a public method; `current` rebinding; identity-copy `patched`; unused `release_update` default; `CREATED_UNITS` from `UNITS`; process-list message helper; services-status helper; start-time parsing once in the manager; owner-file open helper; SHA-256 helpers to `release_stage.sha` where they hash files; `__pycache__`-skipping tree hash once; `REPOSITORY` and bridge-name constants once; `XDG_RUNTIME_DIR` once; `roles` derived from `units` in `ProfileServices`; constant `update_hold` removed from the payload; duplicated reason blocks in `inspect_host`; shared tail of the two `_prepare_*` functions; cross-module private helpers made public where used across modules |
| Smell: format switch | Accept: the format 1 branches are the managed path that design section 11 removes after the transition; a strategy object now would be speculative |
| Smell: private upstream APIs | Accept with a comment at each call site naming the pinned Hermes dependency |
| Smell: long `_run`, `inspect_inplace` | Split where the tests need seams |
