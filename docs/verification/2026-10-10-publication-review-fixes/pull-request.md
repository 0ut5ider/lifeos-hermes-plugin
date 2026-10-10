# feat(lifeos): prepare the daily Discord text release

This candidate governs selected native LifeOS readers and publishers for the first daily Discord text release. It includes the main Pulse dashboard.

The candidate retains the configured private FlashNext tiers. It defers voice, media processing, personal-data migration, and the Pulse core-file editor.

Independent reviews identify publication authority and recovery defects. This candidate corrects those defects.

- Batch publishers check current owner authority between mutations and before they complete receipts.
- Failed consistency checks after publication retain unknown receipts and recovery journals.
- Native recheck conflicts retain the same recovery state.
- Algorithm summaries, LocalIntelligence digests, and Conduit insights verify every destination before they commit receipts.
- Expected-digest recovery preserves later destination edits and refuses before restoring any group member.
- Standalone fixtures omit managed context. Connector-loss tests require refusal for admitted callers.

The maintenance record describes one conditional Hermes patch removal. The current bundle retains all 36 patches and both source pins.

## Validation

The final destination correction passes 166 distinct selected tests without failures, errors, skips, or warnings. Three new test methods exercise 12 destination-change subcases.

All 12 subcases fail before the correction. The corrected cases retain recovery reservations and preserve later destination edits.

The earlier publication correction has passing evidence for 336 distinct selected cases. The two verification groups overlap and must not be added.

All 36 packaged patch copies match their canonical copies. Six approval boundary executions match the patched Hermes pin.

See `docs/verification/2026-10-10-publication-destination-fix/README.md` for final commands, source hashes, results, and limits.

See `docs/verification/2026-10-10-publication-review-fixes/README.md` for the earlier publication verification.

## Release status

The code has review correction evidence. The daily guest is not deployed.

Atlas initialization, private-channel acceptance, final packaging, final recovery, and daily guest deployment remain open release gates.

The staged archive must include all publication corrections before deployment. This change makes no server or Discord configuration change.
