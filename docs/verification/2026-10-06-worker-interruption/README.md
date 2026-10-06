# Killed restore and Hermes patch workers

Date: 2026-10-06. This unit kills the remaining detached workers of the page workflow in the disposable guest CT `100` and recovers them through the page. Production on `.212` stays unchanged.

## LifeOS restore worker

The guest runs plugin `e64e2b1` ([lifeos-restore](lifeos-restore/)). A page update reaches `applied`. A synthetic file is written into `LIFEOS/MEMORY/STATE` after the update. The restore worker receives SIGKILL while its transaction is `restoring`. The page reports `interrupted`/`restoring`. `POST /installation/update/recover` returns the job to `rolled_back`. The synthetic file is present in the restored tree, the gateway is active, VersionDrift reports 0 changes, and a turn answers `READY`.

The first restore request returned HTTP 409 `Another installation operation is running`, because the update status already read `applied` while its worker was still removing its reference tree under the installation lock. A retry after the worker exited succeeded. The page shows the restore button during that interval.

## Hermes patch worker

A first kill of the Hermes restore worker, on plugin `e64e2b1`, left 61 changed Hermes files, a stopped gateway, and the state `restoring`. Every page action refused: restore needs `applied`, and apply needs a clean source. The agent had no route back.

`38e0abd` records the worker unit in the patch manifest, reports `interrupted` when that unit is gone during apply or restore, and adds `POST /installation/recover-hermes`. Recovery writes the original Hermes files, restores the staged config after an interrupted apply, starts the gateway, and checks that the source is clean. The page shows a recovery button.

With `38e0abd` installed ([hermes-patch](hermes-patch/)):

| Kill point | Page state | Recovery result |
| --- | --- | --- |
| Restore worker after the gateway stops, 61 files changed | `interrupted`, `restoring` | `rolled_back`, gateway active, 0 changed files, turn `READY` |
| Apply worker after the gateway stops, before file copy | `interrupted`, `applying` | `rolled_back`, gateway active, 0 changed files, turn `READY` |

Recovery always returns Hermes to its stock files. After an interrupted apply, the owner can apply the patch again.

## Limits

- Each kill point runs once.
- An interrupted apply recovers to stock Hermes, not to the patched state that the owner requested.
- Recovery after a failed recovery (`rollback_failed`) still needs manual repair.
