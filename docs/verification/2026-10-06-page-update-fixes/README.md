# Page update fixes in the disposable guest

Date: 2026-10-06. This unit checks the four fixes for the findings in the [page update unit](../2026-10-06-page-update/README.md). Adrian approved the recommendations on 2026-10-06. The guest CT `100` starts from the snapshot `lifeos-page-60b1446`. That snapshot already contains one turn, so its architecture summary differs from the baseline. The normal Hermes installer replaces the plugin with `bc67f42` ([plugin-update-bc67f42.txt](plugin-update-bc67f42.txt)).

| Finding | Fix | Guest result |
| --- | --- | --- |
| Every update needed a baseline review | `f2669a7`: the generated `ARCHITECTURE_SUMMARY.md` is outside the baseline, the drift check, and the update plan | Drift reads 0 after the earlier turn. The update applies without a review ([update-status.json](update-status.json)). |
| Turns could run during a swap | `987daf3`: turns hold a shared program lock; the worker holds it exclusively | A command-line turn during the `stopped` state receives `LifeOS is updating its installed files` ([turn-during-update.txt](turn-during-update.txt)). The update then reaches `applied`. |
| Restore refused after any turn | `d6ab7cf`: restore carries embedded user data forward and archives the prior copy | A turn after the update writes a transcript into `LIFEOS/MEMORY`. Restore reaches `rolled_back`. The transcript is present in the restored tree and absent from the archived prior copy. Drift reads 0, and a turn answers `READY`. |
| The page showed a stale Hermes state | `bc67f42`: the status reports `dashboard_restart_required` | After the Hermes restore, the page reports `patched_hooks_present` with `dashboard_restart_required: true`. After a dashboard restart, it reports `stock` with `false`. |

## Limits

- The program lock covers turns. Native Pulse and detached asynchronous hooks can still write during a swap.
- The worker waits up to 600 seconds for running turns. Continuous new turns can keep the worker waiting until that limit, and the job then fails before any change.
- On stock Hermes, admission checks the lock but does not hold it, because stock Hermes has no turn-end event.
- The restore carry copies `LIFEOS/MEMORY`, `USER.md`, and `MEMORY.md`. Large memory trees make the copy slower. This unit does not measure that time.
