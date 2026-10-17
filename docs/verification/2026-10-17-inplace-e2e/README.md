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

## Test-host conditions

- The fresh-agent probe constructs a real `AIAgent`, so it needs a configured provider credential. The 110 fixture had none; the runs added a synthetic `OPENROUTER_API_KEY` to `.env`. No model call runs.
- Proxmox host ZFS: stop a container and wait 60 s before a snapshot rollback (OpenZFS #15422). [`crash_matrix.sh`](crash_matrix.sh) does this.
