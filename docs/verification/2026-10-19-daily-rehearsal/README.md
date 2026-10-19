# Daily host layout rehearsal for the in-place 0.8.0-rc.4

Date: 2026-10-19. Rehearsal host: container 115 (`192.168.8.239`), restored from the Proxmox Backup Server backup of daily container 102 taken at 2026-10-19 06:00 UTC. Release: [`v0.8.0-rc.4`](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.8.0-rc.4), program commit `5125f322`.

The daily host was not changed. The rehearsal read the daily host's units and listeners only.

## Why a clone

The daily host has a layout that no earlier test had:

- LifeOS template units (`KillMode=control-group`) that set `HOME` and `LIFEOS_DIR` to a fresh store, and `PYTHONPATH=~/runtime/hermes`.
- A dashboard on `127.0.0.1:18819`, published through Tailscale with a `dashboard.public_url`.
- A gateway with `--external-supervisor`.
- No stock checkout at `~/.hermes/hermes-agent`.
- Nine HTTP memory connections with tokens that agents on other machines use.

A restored backup has the same units, store, configuration, and connections.

## Isolation of the clone

1. The clone has its own address and hardware address, and it does not start at boot.
2. `tailscaled` is masked, so the clone does not join the tailnet as the daily node.
3. The `DISCORD_BOT_TOKEN` line is removed from the clone's `.env`, so the clone does not connect as the daily bot. With an invalid token, the gateway exits ("non-retryable startup conflict"). Without the line, the gateway runs with no messaging platform.
4. The clone is stopped after the rehearsal.

## Steps

1. Baseline: [`check_memory.py`](check_memory.py) recorded each HTTP connection's grant, its live tokens, and how many of them bind to the current memory configuration ([before](memory-before-move.txt)).
2. [`enroll_test.py`](enroll_test.py) added the connection `rehearsal-probe` through `MemoryRemote.enroll`, the code that the dashboard calls. [`mcp_probe.py`](mcp_probe.py) called `lifeos_memory_status` and `lifeos_memory_search` over HTTP with the bearer token. Both returned `ok`.
3. Services stopped. The stock installer ran: `install.sh --commit 71d34bad1045610252eda02ee79549436896e784 --skip-setup`. It exited 0. The checkout is clean at `71d34bad`. The launchers, units, and `.env` stayed byte-identical. The installer rewrote `config.yaml` and added `_config_version: 50`. A parsed comparison shows no other change. On the development host the installer did not change `config.yaml`.
4. `hermes plugins install ... --ref 5125f322... --force` installed the `0.8.0-rc.4` manager. The compatibility check reported a transition.
5. `hermes lifeos-release prepare --version 0.8.0-rc.4` prepared operation `7b6ef9de`. The review listed one configuration key (the bridge source path), no host file list, no created or replaced unit, and the gateway, dashboard, and Pulse roles. The units did not need a change, because they already run `~/.local/bin/hermes`.
6. `hermes lifeos-release start 7b6ef9de65f840e79458673cc5763abf` applied the move.

## Result

| Check | Result |
| --- | --- |
| Operation | `applied` |
| Registration receipt | `{"mode": "patched", "source": "/home/lifeos-hermes/.hermes/hermes-agent"}` |
| Services | gateway, dashboard, and Pulse active, no restarts, `KillMode=control-group`, unit files unchanged |
| `~/.local/bin/hermes` | forwards to `~/.hermes/hermes-agent/.hermes/bin/hermes` |
| `hermes lifeos-version` | `0.8.0-rc.4`, `verified`, host `installed`, no changed files |
| `hermes update` | refused with the LifeOS hold |
| `.env` | unchanged |
| `config.yaml` | the bridge source path and the installer's `_config_version` |
| Memory files | `lifeos-memory.json`, `lifeos-memory-http-credentials.json`, and `lifeos-memory-contexts.json` byte-identical to the baseline |
| HTTP connections | the same grants, and every live token binds ([after](memory-after-move.txt)) |
| HTTP memory | `rehearsal-probe` `status` and `search` return `ok` after the move |
| New connection | `rehearsal-probe-after`, added after the move, returns `ok` |
| OAuth discovery | both metadata documents return 200; a request without a token returns 401 |
| Model reply | `hermes chat -q` with the gateway unit's environment returned `REHEARSAL-OK` |
| Owner login | [`login_probe.sh`](login_probe.sh) set a disposable password on the clone. The password login through the public host returned 200 with the `basic` session `adrian`. The release manager installation, compatibility, and operations APIs and the memory and HTTP memory settings APIs returned 200. |
| Pulse | listens on `127.0.0.1:18837`; `PULSE.toml` with the `0 7 * * *` schedule is unchanged |
| Hermes cron | no jobs, the same as the daily host |

A non-loopback `dashboard.public_url` makes Hermes require a login on a loopback bind. Thus the release manager and memory owner pages work on the daily layout.

## Rollback

`hermes lifeos-release rollback 7b6ef9de65f840e79458673cc5763abf` reached `rolled_back`. The launcher forwards to the managed job `3e74ddd4` again. `hermes lifeos-version` reports `0.7.3`, `verified`. The three services are active. The Hermes checkout is clean. `config.yaml` equals the state after the installer. HTTP memory returns `ok`. The connections that were added during the in-place period stay.

## Not covered

- Discord delivery. The development host covers Discord on the in-place release.
- An automatic 07:00 morning run.
- The owner pages in a browser. The rehearsal called the same APIs with a session cookie.

## Clone state

Container 115 is stopped at the in-place state with the disposable password. Snapshots: `rehearsal-start`, `rehearsal-enrolled`, `rehearsal-applied`. The clone holds a copy of the daily data. Delete it with `pct destroy 115` after the daily move.
