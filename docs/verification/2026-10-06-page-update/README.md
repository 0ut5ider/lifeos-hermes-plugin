# LifeOS update, interruption recovery, and restore from the plugin page

Date: 2026-10-06. This unit continues the [page installation unit](../2026-10-06-page-install/README.md) in the disposable guest CT `100`. Each part starts from the guest snapshot `lifeos-page-60b1446`. The normal Hermes installer first replaces the plugin with `03cc56d`. Production on `.212` stays unchanged.

All requests use [pageclient.py](pageclient.py) through a real dashboard password session. The client keeps one private session cookie file. An earlier version signed in for every request and reached the Hermes login rate limit (HTTP 429) during polling.

## Plugin update with LifeOS installed

The forced plugin installation keeps the plugin enabled. After a service restart, the page reports LifeOS `installed`, the patched Hermes hooks, a ready candidate, and a committed mount. Doctor registers 9 hooks ([update-and-restore](update-and-restore/)).

## LifeOS update

1. The first update fails before any change: `Installed LifeOS system file changed since baseline: LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md`. The native `RebuildArchSummary` hook rewrites the `last_updated` timestamp of that file on each turn.
2. The owner reviews the drift through `/version-drift/preview` and renews the baseline with the preview fingerprint. One changed file is reviewed.
3. The second update passes through `stopped` and `swapped` to `applied` in about 60 seconds. A turn answers `READY`.

## Interruption recovery

[interruption](interruption/) holds these records.

| Kill point | Page state after SIGKILL | Recovery result |
| --- | --- | --- |
| Transaction `stopped`, gateway stopped | `interrupted`, `stopped` | `rolled_back`, gateway active, zero drift |
| Transaction `swapped` | `interrupted`, `swapped` | `rolled_back`, gateway active, zero drift |

The test sends SIGKILL to the detached worker unit with `systemctl --user kill`. The owner then sends `POST /installation/update/recover`.

## Restore

After a third update reaches `applied`, `POST /installation/update/restore` returns `rolled_back`. The gateway is active, drift is zero, and a turn answers `READY`. In this run, a command-line turn ran while the update was still applying. The update and the restore both completed.

In the first part, a turn after `applied` changes 19 files in the embedded `LIFEOS/MEMORY` tree. The restore route then refuses with `User data changed after update; automatic restore refused`. A synthetic note in the linked `LIFEOS/USER` directory is not the cause: the refusal remains after the note is removed.

## Hermes patch restore

`POST /installation/restore-hermes` returns the host patch to `rolled_back`. The Hermes checkout has zero changed files. The gateway is active. After a dashboard restart, the page reports `hermes: stock`, doctor registers 6 hooks, and a turn answers `READY`.

## Findings

1. Every turn changes a tracked LifeOS system file. Each LifeOS update therefore needs a manual baseline review first. The changed bytes are a generated timestamp.
2. Restore is refused after any turn that follows an update, because turns write to the embedded `LIFEOS/MEMORY` tree. On a page installation, `LIFEOS/MEMORY` is a directory inside `~/.claude`; only `LIFEOS/USER` is linked outside it. The restore workflow therefore works only before the agent is used.
3. The update stops the gateway, but command-line turns can still run and write to the installed tree during the swap. This run did not show damage. This unit does not prove that such writes are safe.
4. The dashboard keeps the Hermes hook list that it loaded at start. After a host patch or a host restore, the page reports the earlier state until the dashboard restarts.

## Limits

- The update target is the same LifeOS revision. This unit does not show compatibility with a later upstream revision.
- Kill tests cover the `stopped` and `swapped` states of the LifeOS update. They do not cover the restore worker or the Hermes patch worker.
- Identity, memory ownership, Pulse, and messaging are not configured.
