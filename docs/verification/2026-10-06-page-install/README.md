# LifeOS installation from the plugin page on stock Hermes

Date: 2026-10-06. This unit installs LifeOS through the plugin page API in the disposable guest CT `100` on `192.168.8.101`. The guest starts from stock Hermes `758ad514` with the plugin installed by the normal Hermes installer ([stock installation unit](../2026-10-05-stock-plugin-install/README.md)). Production on `.212` stays unchanged.

## Guest preparation

1. The root user enables systemd linger for `hermes` and installs `unzip`. The Bun installer needs `unzip`.
2. The user `hermes` installs Bun 1.3.14, the version in the plugin dependency catalog.
3. `hermes gateway install` creates and starts the gateway user service.
4. A dashboard user service runs `hermes dashboard --host 0.0.0.0 --port 9119 --skip-build --no-open`. The bundled basic authentication provider reads a generated user name, password, and session secret from a private file in the guest. These values are not in this repository.
5. [pageclient.py](pageclient.py) signs in through `/auth/password-login` and calls the plugin routes with the dashboard origin.

A loopback dashboard bind disables the Hermes authentication gate. The plugin then sees no session and refuses its owner routes with HTTP 401. The page workflow therefore needs a non-loopback bind with a password or OAuth provider.

## First attempt

The guest runs plugin `659246a`.

1. `POST /installation/prepare` clones LifeOS `5e2f2e8` from GitHub and applies the ten patches.
2. The first `POST /installation/apply` fails: `LifeOS DeployCore exited with code 1`. The route does not return the tool output. The same installer passes four times in a diagnostic process, with a cold and a warm Bun cache, in a scratch root and in the real home. After a snapshot rollback, the page apply passes. The cause of the first failure is not known. It did not occur again.
3. `POST /installation/finalize` fails: `LifeOS Hermes prepared config check exited with code 1`. The transaction restores the profile.
4. `POST /installation/prepare-hermes` and `POST /installation/apply-hermes` pass. The host patch reaches `applied`.

[attempt-1](attempt-1/) holds the responses after the rollback.

## Root cause of the finalize failure

Stock Hermes writes `plugins.enabled` after a column-zero section banner inside the `plugins:` mapping. Native `Mount.ts` ended the block at the first column-zero line. It therefore did not find the existing list and inserted a second `enabled:` key. The Hermes YAML loader refuses the duplicate key, so the prepared config check fails on every stock installation. The approvals deny list used the same block scan. On the same layout, it skipped reconciliation.

The patch `lifeos-mount-yaml-blocks.patch` keeps column-zero comments inside a top-level block for both editors. Two regression tests run native `Mount.ts` and the actual Hermes config check on the stock layout. [before.txt](before.txt) shows both tests failing for the expected reasons. [after.txt](after.txt) shows 17 mount tests passing. [gate.txt](gate.txt) passes 91 tests in nine groups without skips, including real-source preparation from the LifeOS and Hermes repositories.

## Second attempt

The guest returns to the snapshot `services-659246a`. The normal Hermes installer replaces the plugin with `60b1446` ([plugin-update-60b1446.txt](attempt-2/plugin-update-60b1446.txt)).

| Step | Result |
| --- | --- |
| prepare | HTTP 200, LifeOS `5e2f2e8` with 11 patches |
| apply | HTTP 200, LifeOS 7.40.4, frozen dependencies with Bun 1.3.14 and 12 packages |
| finalize | HTTP 200, mount `committed`, VersionDrift baseline created |
| prepare-hermes | HTTP 200, Hermes `758ad514` with 9 patches |
| apply-hermes | HTTP 200, detached worker, state `applied`, gateway restarted |

After these steps, `hermes config check` passes. `hermes plugins doctor lifeos-hook-bridge` registers 9 hooks. Its warning about `pre_llm_call` is expected: on a patched host, the plugin registers `pre_prompt_admission` instead. A one-shot turn against private FlashNext answers as LifeOS ([turn.txt](attempt-2/turn.txt)). The turn writes LifeOS state, observability, gate, and transcript records under `~/.claude/LIFEOS/MEMORY`.

The guest snapshot `lifeos-page-60b1446` retains this state.

## Findings and limits

- The dashboard process keeps the stock Hermes hook list after the host patch. The page reports `hermes: stock` until the dashboard restarts. The worker restarts only the gateway.
- The installation and mount routes report a native exit code without the tool output. The first apply failure therefore has no recorded cause.
- The assistant name is the LifeOS default. This unit does not configure identity, memory ownership, Pulse, or messaging.
- This unit does not test a LifeOS update, its restore, interruption recovery, or the Hermes patch restore.
