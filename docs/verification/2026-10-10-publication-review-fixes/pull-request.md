# feat(lifeos): prepare the daily Discord text release

This candidate governs selected native LifeOS readers and publishers for the first daily Discord text release. It includes the main Pulse dashboard.

The candidate retains the configured private FlashNext tiers. It defers voice, media processing, personal-data migration, and the Pulse core-file editor.

The independent review finds two publication defects. This candidate corrects both defects.

- Batch publishers check current owner authority between mutations and before they complete their receipts.
- Failed consistency checks after publication retain unknown receipts and recovery journals.
- Native recheck conflicts preserve the same recovery state.
- Recovery preserves concurrent owner edits.
- Standalone fixtures omit managed context. Connector-loss tests require refusal for admitted callers.

The maintenance record describes one conditional Hermes patch removal. The current bundle retains all 36 patches and both source pins.

## Validation

The selected combined checks have passing evidence for 336 distinct cases. The final recovery gate passes 12 cases.

The latest publisher regression passes 50 cases. Complete source preparation passes all four cases with real pinned repositories.

All 36 packaged patch copies match the canonical copies. Six approval boundary executions match the patched Hermes pin.

See `docs/verification/2026-10-10-publication-review-fixes/README.md` for commands, source identities, results, and limits.

## Release status

The candidate remains staged. The daily guest is not deployed.

Atlas graph initialization, private-channel acceptance, final packaging, final recovery, and daily guest deployment remain open.

The staged archive must include the publication corrections before deployment. This change makes no server or Discord configuration change.
