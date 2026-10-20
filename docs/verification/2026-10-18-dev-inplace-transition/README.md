# Development host move to the in-place 0.8.0-rc.1

Date: 2026-10-18. Host: development container 101 (`192.168.8.252`, account `lifeos-hermes`). Release: [`v0.8.0-rc.1`](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.8.0-rc.1), program commit `a0fbeb48`, package SHA-256 `5036e42845f160d92c18073721b5ed30616dc7f399d51d8a1c944375289f2653`.

The owner approved the move of the development host only. The daily host stays on managed 0.7.3.

## Starting state

- Managed 0.7.3 (`70fa8390`), `verified`, job `430bac10...`.
- The gateway and dashboard units ran `~/workspace/hermes-agent/.hermes/bin/hermes`, a forwarder to the managed runtime inside another Hermes checkout (review item R2-1). Pulse ran `~/.local/bin/bun`.
- No stock checkout at `~/.hermes/hermes-agent`.
- Discord connected.

## Steps

1. Proxmox snapshot `lifeos-080rc1-pre-transition-20261018` of container 101.
2. Backup in `~/transition-backup-20261018`: `config.yaml`, `.env`, the user units, `~/.local/bin`, the workspace forwarder, file hashes, and later the 0.7.3 release manager directory.
3. The gateway and dashboard `ExecStart` lines changed from the workspace forwarder to `~/.local/bin/hermes`, followed by `daemon-reload` and a restart. No other unit line changed. Both units stayed active on the managed runtime.
4. Services stopped. The stock installer ran: `install.sh --commit 71d34bad1045610252eda02ee79549436896e784 --skip-setup`. It exited 0. The optional `cua-driver` tool failed its own verification, which is a warning. The launchers, `.env`, and `config.yaml` stayed byte-identical. The checkout is clean at `71d34bad`. Services started again on the managed runtime, `verified`.
5. `hermes plugins install '<repository>.git#optional/lifeos_release_manager' --ref a0fbeb48... --force` replaced the 0.7.3 manager with `0.8.0-rc.1`. `hermes lifeos-release compatibility` reported `compatible`, `transition: true`, and no added packages.
6. `hermes lifeos-release prepare --version 0.8.0-rc.1` refused with "Use an update for the existing LifeOS installation". The rc.1 command line passed no intent, and the in-place path read that as a first installation. Commit `d6bbdd90` fixes the command line. The move used the same rc.1 function with the update intent, as the release dashboard does (`cli.prepare(profile, '0.8.0-rc.1', intent='update')` under the managed runtime). Operation `db96356e` reached `ready`.
7. The review listed one configuration key (`plugins.entries.lifeos-hook-bridge.settings.lifeos_source_dir`), no replaced unit, and the gateway, dashboard, and Pulse roles.
8. `hermes lifeos-release start db96356ed19e4248819386c86fabc6ac` applied the move.

## Result

| Check | Result |
| --- | --- |
| Operation | `applied` |
| Registration receipt | `{"mode": "patched", "source": "/home/lifeos-hermes/.hermes/hermes-agent"}` |
| Services | gateway, dashboard, and Pulse active and enabled |
| `~/.local/bin/hermes` | forwards to `~/.hermes/hermes-agent/.hermes/bin/hermes` |
| `hermes lifeos-version` | `0.8.0-rc.1`, `verified`, host `installed`, no changed files |
| `hermes update` | refused with the LifeOS hold |
| `.env` | unchanged |
| `config.yaml` | only the bridge source path changed |
| Discord | `connected`; the gateway reports code `71d34bad`, version `0.21.7` |
| Dashboard | answers on port 9119 |

## Update to 0.8.0-rc.4

Later on 2026-10-18 the development host updated in place from `0.8.0-rc.1` to [`v0.8.0-rc.4`](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.8.0-rc.4) (program commit `5125f322`).

1. Proxmox snapshot `lifeos-080rc4-pre-update-20261018`.
2. `hermes plugins install '<repository>.git#optional/lifeos_release_manager' --ref 5125f322... --force` installed the `0.8.0-rc.4` manager. The compatibility check reported `installed`.
3. `hermes lifeos-release prepare --version 0.8.0-rc.4`, with no intent, prepared the update (`94e102f2`). The rc.1 command line had refused this. The review listed no host file change, one configuration key (the bridge source path), and the gateway, dashboard, and Pulse roles.
4. `hermes lifeos-release start 94e102f231214c41b42ae11ee9b447a6` applied it.

Result: `applied`; receipt from `/home/lifeos-hermes/.hermes/hermes-agent` in patched mode; the three services active; `hermes lifeos-version` reports `0.8.0-rc.4`, `verified`, and no host drift; `.env` unchanged; `config.yaml` changed only in the bridge source path; `hermes update` refused with the hold; Discord `connected`.

## Retained for rollback

- The Proxmox snapshot and the backup directory.
- The managed job directories stay until the owner approves their removal. The workspace forwarder still points at managed job `430bac10...`; no unit runs it.

## Known limits on this host

- With `0.8.0-rc.1`, complete removal read the dashboard login only from `config.yaml`, and this host supplies the login through `EnvironmentFile=.../dashboard-auth.env`. Since `0.8.0-rc.3`, the removal plan records the login of the dashboard that authorizes the removal, so this limit does not apply to `0.8.0-rc.4`. See the [container record](../2026-10-17-inplace-e2e/README.md).
