# Governed staged decisions

Date: 2026-10-08. Scope: the daily text release candidate. Installed ownership remains disabled.

The [initial experiment](before.txt) exercises actual native rejection and managed promotion. It finds three failures and one error in five cases. Native rejection deletes queued notes without a managed receipt. Promotion can publish after caller authority changes during index rendering.

Managed native rejection now uses the current owner scope and a recoverable transaction. It binds a bounded selector to regular, private queue files. It rechecks source identity and authority before deletion. A repeated request returns the existing receipt after the files disappear. Rejection preserves the native harvest state. Standalone rejection retains its existing behavior.

The [source-race experiment](race-before.txt) finds two further failures. A staged note or harvest state can change during the final index render. Promotion now compares both sources after rendering and authority verification. It returns a conflict and preserves concurrent edits.

The [combined gate](focused.txt) passes 114 tests without skips. It includes twelve staging writer controls, actual native tools, source and authority changes, private file admission, idempotent retry, and real process interruption during bulk deletion. Recovery restores both queued notes after that interruption. The next governed rejection succeeds. Existing native facts, promotion, indexes, private publication, transaction recovery, and source installation checks also pass.

The [source preparation](source-preparation.txt) applies all eleven Hermes patch groups and twenty-three LifeOS patch groups to the pinned revisions. The [runner](run_gate.py) records its exit status in `focused.done`.

This unit does not govern native KnowledgeHarvester source mining or stale-note expiry. Those writers, scheduled execution, installed activation, live Discord audience checks, and combined release acceptance remain open. No candidate application code deploys in this unit.
