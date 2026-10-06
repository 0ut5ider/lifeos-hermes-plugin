# Detached fresh-store preparation

Date: 2026-10-05. Fresh-store preparation now runs outside the dashboard request. Production on `.212` stays unchanged.

## Behavior

`POST /memory/fresh/start` checks the owner and the two display names, creates an identifier, and starts `fresh_store_worker.py` as the systemd user unit `lifeos-fresh-store-<identifier>`. The route returns HTTP 202 with the identifier. The unit continues when the dashboard or the gateway restarts. The route refuses extra request fields with HTTP 400, a missing session with HTTP 401, and a revoked owner binding with HTTP 403.

The worker runs the existing preparation under the installation lock. When preparation fails, the worker records the state `failed` with the names and a short reason. The status listing therefore separates four outcomes: `review`, `preparing`, `failed`, and `interrupted`.

`DELETE /memory/fresh/stores/<identifier>` removes one prepared store. It refuses a running installation operation, an unknown or malformed identifier, a linked directory, another owner, and the store of the selected installation. It does not touch other stores or the current profile.

The synchronous `POST /memory/fresh/prepare` route stays for the existing tests and clients.

## Verification

The new tests fail before the implementation ([before.txt](before.txt)). The final gate passes 41 tests without skips ([after.txt](after.txt)). It includes these native cases with the complete prepared LifeOS candidate:

- The detached worker reaches `review` with Adrian and Cerebo and zero active facts.
- A worker whose complete process tree is killed during installation is listed as `interrupted`, and the removal action deletes its store.

The interruption test ends every descendant process, because the installer starts its children in their own sessions. A stopped systemd unit ends its whole control group in the same way.

## Limits

- The route test replaces the systemd launcher with a direct process start. No test starts the actual systemd unit; that check belongs to the browser and service acceptance on a real profile.
- A reboot during preparation leaves an `interrupted` store. Preparation does not resume; the owner removes the store and starts again.
- The dashboard page has no controls for these routes yet.
