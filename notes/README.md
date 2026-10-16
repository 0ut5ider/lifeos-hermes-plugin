# Engineering notes

These dated notes preserve measured causes, rejected approaches, decisions, and investigation limits. Use the [active documentation index](../docs/README.md) for current user instructions and the [codebase map](../docs/codebase.md) for implementation entry points.

A note describes its checkpoint. An old host, patch count, or open release gate does not override a later qualified release. Keep the original observation and link a correction instead of rewriting an earlier failure as success.

Useful entry points:

- [Conditional Hermes patch reduction](2026-10-10-conditional-hermes-patch-reduction.md): earlier 36-to-35 proposal and required checks. The current active count is in the [patch map](../docs/patch-footprint.md).
- [Setup stylesheet cause](2026-10-16-plugin-setup-styles.md): measured unstyled controls and theme assumptions behind 0.7.2.
- [Direct child inference](2026-09-28-direct-child-inference.md): earlier model-route probe and limits.
- [Source manifest collision](2026-09-28-source-manifest-runtime-collision.md): why source preparation writes `source-manifest.json`.

Use `git ls-files notes` and search for the task's module, command, or symptom. Keep private raw evidence outside Git; publish only the safe finding and relevant source or receipt references.
