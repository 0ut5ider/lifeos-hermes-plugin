# In-place installation qualification on containers

Date: 2026-10-17. Release candidate: 0.8.0-rc.1, branch `feature/minimal-install-review`. Hermes: stock `v0.21.7` (`71d34bad1045610252eda02ee79549436896e784`).

These runs exercise the in-place release on disposable Proxmox containers. They use the release manager functions through [`driver.py`](driver.py) and a loopback release server ([`scripts/local_release_server.py`](../../../scripts/local_release_server.py)) with a test certificate. They do not use the GitHub plugin URL, a published release, or the dashboard buttons. Those remain open in the [plan](../../in-place-installation-plan.md).

## Hosts

| Container | Purpose | Starting state |
| --- | --- | --- |
| 110 | In-place install, update, memory return, removal | Stock `install.sh --skip-setup`, stock gateway unit, third-party `weather-test` plugin with a Python dependency, custom model entry, an MCP server |
| 112 | Crash recovery | Copy of 110 before installation |
| 114 | Managed-release transition | Managed 0.7.3 installed from GitHub, stock checkout installed afterwards |

[`redeploy.sh`](redeploy.sh) builds the integration package from `HEAD`, stages it, and replaces the installed release manager so that the new preparation code runs. That replacement makes the installed manager differ from its release record. Run a real update before a removal, or the removal refuses with "A release program differs from its qualified identity".

## Results

| Flow | Build | Result |
| --- | --- | --- |
| First installation on 110 | An earlier build of this branch (snapshot `extras-installed`) | Applied. The gateway registered the bridge in patched mode. `weather-test` and its dependency stayed installed. |
| Interrupted first installation, 4 checkpoints on 112 | `b07c2205` | All 4 recovered to `applied` ([results](crash-results/)): `programs-published`, `dependencies-synchronized`, `native-mounted`, `artifact-published` |
| `hermes update` on installed 112 | `b07c2205` | Refused with the LifeOS hold message. `HEAD` stayed at `71d34bad` and all 96 patched paths stayed in place. |
| Update on 110 | `812735d6` | Applied (`f3e8c19f`) |
| Memory claim, export, and provider return on 110 | `812735d6` | Verified after one recovery. The first verification failed once, immediately after the update; its cause was not recorded (see defect 6). |
| Software removal on 110 | `812735d6` | Verified (`27d62894`) |
| Removal rollback on 110 | `b19e793e` | Rolled back through the retained `recover rollback` command after defect 5 was cleared by hand |
| Managed 0.7.3 to in-place transition on 114 | `812735d6` | Applied (`812e0628`). The gateway runs the stock checkout. |
| Restore of that transition on 114 | `812735d6` | Rolled back to the managed runtime, all services active |

### Regression after the PR 40 review fixes

Build `9f1749d3` adds the post-restart checks (per-unit start time, enabled state, capability probe, memory provider). On that build:

| Flow | Result |
| --- | --- |
| Managed 0.7.3 to in-place transition on 114 | Applied (`dea9b27a`), receipt `{"mode": "patched", "source": "/home/lifeos-hermes/.hermes/hermes-agent"}` |
| Restore of that transition on 114 | Rolled back to the managed runtime, all services active |
| In-place update on 112 | Applied (`c288d8d2`), receipt `{"mode": "patched", "source": "/home/owner/.hermes/hermes-agent"}` |

The first attempt on this build failed in preparation on both hosts, because `scripts/local_release_server.py` imported the plugin package, which the harness does not copy. Commit `9f1749d3` fixes the script.

### Final regression on `7d76fc6c`

| Flow | Result |
| --- | --- |
| Managed 0.7.3 to in-place transition on 114 | Applied (`1c0c6613`), receipt from `/home/lifeos-hermes/.hermes/hermes-agent` |
| Restore of that transition on 114 | Rolled back to the managed runtime, all services active |
| In-place update on 112 | Applied (`128c506b`), receipt from `/home/owner/.hermes/hermes-agent` |
| In-place update on 110 from its first-install snapshot | Applied (`b49e4642`), receipt from `/home/owner/.hermes/hermes-agent` |

On 110 after the first installation (snapshot `extras-installed`), the Pulse unit exists and is disabled and inactive. An attempt to install LifeOS again after the verified removal on 110 found that this flow is not supported; the design records the limit.

### Removal end state on 110

- The Hermes checkout is clean at `71d34bad` (`git status` reports nothing).
- The plugin directory holds only `weather-test`. The Pulse unit is gone. The gateway is active.
- `lifeos-host.json`, `.lifeos-host/`, and the update hold are gone.
- `.env` lost only the LifeOS block. An owner line added after installation is intact.
- `config.yaml` lost the values that LifeOS recorded with no earlier value: `approvals`, `context_file_max_chars`, and `file_tools`. The LifeOS plugin entries are gone, `memory` selects the built-in stores, and Discord is disabled because the run requested it.
- `~/.claude` and the built-in memory files remain, as designed.

### Transition end state on 114

- `~/.local/bin/hermes` forwards to `~/.hermes/hermes-agent/.hermes/bin/hermes`.
- `hermes-gateway.service` is the unit that stock `generate_systemd_unit()` writes for that checkout.
- The registration receipt reads `{"mode": "patched", "source": "/home/lifeos-hermes/.hermes/hermes-agent"}`.
- The `config.yaml` change is limited to the LifeOS plugin source path and a re-indentation of two lists. The protected-settings check passed and the configuration record lists no protected change.

## Defects found and fixed in these runs

1. **Unit stop timeout.** The service controller allowed 45 s for a stop. The managed Pulse unit took 45.2 s, so the transition rolled back. Fixed in `b19e793e`: the controller waits 300 s.
2. **Transition left the gateway on the managed runtime.** The gateway unit kept the managed launcher and `PATH`. The patched receipt did not detect it, because the managed Hermes is also patched. Fixed in `9331c723` (see the [design, section 10](../../in-place-installation-design.md)).
3. **Removal joined an owner `.env` line onto a comment.** The removal deleted the LifeOS block with its leading line break. Fixed in `51f7a698`.
4. **Probe wrote bytecode into retained recovery code.** The fresh-agent probe ran isolated (`-I`), which ignores `PYTHONDONTWRITEBYTECODE`. The recovery command then refused its own bridge copy as an unreviewed artifact. Fixed in `812735d6`.
5. **Workflow failures left no cause.** The detached worker discarded the exception. Fixed in `812735d6` (`worker-failure.json`) and `d904d158` (`probe-output.txt`).
6. **Return verification failed once after an update.** A second attempt verified. The run predates the probe-output fix, so the cause is unknown.

## Defects found by review and the development host

The [independent review](../../agents/2026-10-17-inplace-fixes-review/inplace-fixes-review.md) and a read-only inspection of the development host found these transition defects. Commit `8d009e25` fixes them. The transition and its restore on 114 pass again on that build.

7. **Adoption before reload.** A replaced unit file reports `NeedDaemonReload=yes` until the manager reloads, and service inspection refuses that state. A failure between publication and reload would leave the host in `recovery_required`. The worker now reloads before adoption.
8. **Template gateway units.** A fresh managed installation writes its gateway unit with `KillMode=control-group` and the account launcher. Stock Hermes writes `KillMode=mixed`, so adoption would refuse the replacement after publication. Preparation now keeps a unit that runs the account launcher. It refuses a replacement that changes `KillMode` or `WorkingDirectory`, a symlinked unit, and a drop-in that runs the managed runtime.
9. **Service launchers outside `~/.local/bin`.** On the development host, the gateway and dashboard units run `~/workspace/hermes-agent/.hermes/bin/hermes`. The managed release rewrote that file into a forwarder to its runtime. The 0.8.0-rc.1 candidate first published a stock forwarder at each launcher in the managed job's `plan.json`. After review item R2-1, preparation refuses such a unit instead, and the owner points it at `~/.local/bin/hermes`. Preparation reads each unit command from `systemctl --user show`, so drop-ins and specifiers apply.

### Service launcher refusal on 114, build `80057d6d`

The rehearsal copied the managed account forwarder to `~/workspace/hermes-agent/.hermes/bin/hermes` and pointed the dashboard unit at it with a drop-in that uses `%h`.

| Step | Result |
| --- | --- |
| Transition with the dashboard on the workspace forwarder | `preparation_failed`: "The hermes-dashboard.service unit runs /home/lifeos-hermes/workspace/hermes-agent/.hermes/bin/hermes, which runs the managed runtime." |
| Transition after removal of the drop-in (dashboard on `~/.local/bin/hermes`) | Applied (`e4678b03`), receipt from `/home/lifeos-hermes/.hermes/hermes-agent` |
| Restore of that transition | Rolled back to the managed runtime, all services active |

The daily host uses only `~/.local/bin/hermes` and template units, which the 114 rehearsal does not reproduce exactly (114 has a stock-format gateway unit).

## Published prerelease, GitHub URL, and dashboard buttons on 112

Date: 2026-10-18. Release: [`v0.8.0-rc.1`](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.8.0-rc.1), program commit `a0fbeb48`, archive SHA-256 `5036e428...2653`. Two builds from that commit gave the same archive hash. Before publication, the archive passed the transition and its restore on 114 through the loopback server (`a5d1f2c8`).

Starting state: 112 rolled back to its `base` snapshot (stock `v0.21.7`, gateway unit, `weather-test`, custom model, MCP server, no LifeOS). The dashboard ran by hand on `0.0.0.0:9119` with a test password login. A synthetic `OPENROUTER_API_KEY` let Hermes resolve the configured model provider; no model request ran.

| Step | How | Result |
| --- | --- | --- |
| Install the release manager | `hermes plugins install '<repository>.git#optional/lifeos_release_manager' --ref a0fbeb48... --force` | Installed `0.8.0-rc.1`. The scanner gives a CAUTION verdict, so the command needs `--force`. |
| Compatibility | Releases page | "LifeOS can be installed", `v0.21.7`, two added Python packages |
| Install | Version `0.8.0-rc.1`, **Install LifeOS**, **Review release**, **Install this release** | Applied (`87742d32`). The prepared package hash matches the published asset. Receipt from `/home/owner/.hermes/hermes-agent` in patched mode. `hermes lifeos-version` reports `verified` and no host drift. `hermes update` refuses with the hold. |
| Claim and export | LifeOS Bridge page: **Claim**, **Review reverse export**, **Create reviewed export** | Claimed and exported |
| Provider return | **Prepare return to built-in Hermes**, then **Apply reviewed provider return** | First run `interrupted`: the fresh-agent check could not resolve the model provider before the synthetic key existed. **Recover memory workflow** then verified it. |
| Removal | Acknowledgement, **Prepare complete LifeOS removal**, **Remove reviewed LifeOS software** | Verified (`22558182`). The checkout is clean at `71d34bad`, the hold and host record are gone, `weather-test` remains, and the gateway runs stock Hermes. |

Findings from this run, none of which blocks the transition:

1. The Hermes **Plugins** page has no field for a Git ref. A URL install there takes the default branch, so it installs the 0.8.0 manager only after this branch merges. Before that, use the command line with `--ref`.
2. The release manager accepts only an authenticated dashboard session. A dashboard bound to `127.0.0.1` does not attach password sessions, so the releases page needs a non-loopback bind with a login provider.
3. Complete removal reads the dashboard login from `config.yaml` (`dashboard.basic_auth`). A login supplied only through environment variables refuses removal preparation with "Complete removal currently requires a password-authenticated dashboard recovery owner". The development host supplies its login through an `EnvironmentFile`.
4. Provider return and removal need a model provider that Hermes can resolve, although no model request runs.
5. Before the owner claims the installation, the releases page reports "Memory workflow status is unavailable under this profile" instead of pointing to the claim.
6. Memory administration finds `bun` through `PATH` only. A dashboard started without `~/.local/bin` on `PATH` reports "No such file or directory: 'bun'". Other callers fall back to `~/.local/bin/bun`.
7. The LifeOS Bridge page still shows the managed-release text "Prepare latest LifeOS update" on an in-place installation.
8. The review did not offer a unit for the hand-started dashboard that served the request.

## Unit tests

The suite ran per module (429 modules) on this branch, while commits `7511580d` to `8d009e25` landed, with the prepared sources from the 0.7.3 package and its pinned Bun locks. 81 modules failed. The same 81 modules ran on `origin/main` (`06ea5746`) in the same environment:

- 79 fail there as well. Most need fixture variables that this environment does not set (`LIFEOS_HARVEST_CONTROL_SOURCE`, `LIFEOS_FRESHNESS_CONTROL_SOURCE`, a separate memory test interpreter). Two call `hermes_cli.plugins.unload_plugins`, which Hermes `v0.21.7` does not have.
- `test_memory_local_refresh_lifetime` passes alone on this branch; it failed under the parallel run.
- `test_release_accounts` drove the replaced managed preparation. Commit `29c8d94c` points it at the in-place preparation.

These results do not cover the suites that need the missing fixtures.

## Test-host conditions

- The fresh-agent probe constructs a real `AIAgent`, so it needs a configured provider credential. The 110 fixture had none; the runs added a synthetic `OPENROUTER_API_KEY` to `.env`. No model call runs.
- Proxmox host ZFS: stop a container and wait 60 s before a snapshot rollback (OpenZFS #15422). [`crash_matrix.sh`](crash_matrix.sh) does this.
