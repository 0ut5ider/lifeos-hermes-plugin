# Concurrent hook state publication

Date: 2026-10-06.

Four real concurrent sentinel edits produce one completed evaluation, but a native ConfigEvalFire hook also emits `ENOENT` when it renames `config-eval-state.json.tmp`. The evaluator's single-run lock works. The fire-state publisher uses one temporary filename across hook processes.

A control delays each actual state write before rename. Fifteen of sixteen concurrent hook processes fail before the correction. The patch changes only temporary-file identity and exclusive creation. All sixteen then complete with empty stderr and valid JSON state. A real four-edit repeat completes exactly one private FlashNext evaluation on each comparison side without a hook error.

The distinction matters: a completed evaluation did not prove that all hook calls succeeded. The retained operation results now require both the completed real evaluation and clean hook output.
