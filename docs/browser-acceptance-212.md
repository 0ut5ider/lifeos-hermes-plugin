# Browser acceptance on the separate .212 installation

Date: 2026-10-02

## Open the installation

1. Open [Hermes chat](http://192.168.8.212:8921/chat) from a computer on the local network.
2. Sign in as `adrian`. The private login file on the workstation contains the password. It is outside this repository.
3. Open [LifeOS Bridge preferences](http://192.168.8.212:8921/lifeos-bridge?profile=default) to inspect the installation and model choices.

The login file is `/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002/browser-login.json`. The server has a private copy at `/home/lifeos-plugin-install-probe/acceptance-20261002/browser-login.json`. Neither file is a release artifact.

This installation uses a separate home under the `lifeos-plugin-install-probe` account. It imports no production conversation or memory data. The existing `.212` installation and both `.211` and `.213` remain unchanged.

## What to test now

| Test | Suggested interaction | Expected result |
| --- | --- | --- |
| Ordinary conversation | Ask, "Tell me what LifeOS adds to this assistant." | The assistant replies through the private local model. |
| Tool execution | Ask, "Use the terminal tool to run pwd and tell me the directory." | The assistant uses the tool and reports the real directory under the acceptance home. |
| Working with files | Ask the assistant to create a small test note in its workspace, read it, then change one sentence. | The file changes agree with the answer. The recorder captures the applicable read and edit hooks. |
| Conversation history | Start another chat, then reopen the earlier session. | Hermes retains the earlier messages. A new chat has a separate session. |
| Model choices | Inspect the four LifeOS model rows. | The rows select configured Hermes models and effort levels. These choices apply to LifeOS helper calls. |
| Failure reporting | If an operation fails, ask the assistant to report the failure and its reason. | The answer agrees with the actual tool result. We can compare that result with the private hook trace. |

Record the approximate time, the session, the request, and the result when behavior looks wrong. A screenshot helps. The development recorder captures hook selection, execution, decisions, and tool boundaries so an agent can trace the same session later.

## Current memory limit

Lasting-memory ownership and external memory sharing remain disabled. This browser installation can test chat, tools, hook dispatch, native mounting, and installation controls. It is not the final acceptance environment for the complete LifeOS memory experience.

Do not use this installation as the sole copy of important information. The memory acceptance work still includes remaining native readers and derivatives, restricted prompt and delivery paths, retained-session reconstruction, and recoverable ownership setup. Established-profile import and removal also remain planned.

## Installation controls

The tested LifeOS revision is 7.40.4 at commit `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. The tested Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`. The plugin prepares a supported revision with its tested patch set. A newer upstream revision can require compatibility work before the plugin offers it.

The browser completes native installation and setup. A real detached worker applies a same-revision update and restarts the gateway. The interrupted-mount control restores verified previous bytes and permissions after a killed process.

`Restore previous LifeOS version` restores the saved program snapshot and keeps current external LifeOS user data. The transaction verifies the recorded directory links and physical target identities before the swap. A live browser rehearsal adds a synthetic audit entry after the update. Restore preserves all 321,597 audit bytes and the original file identity. Changed embedded data, replaced links, and later Hermes profile changes still refuse restoration. The [PR readiness record](verification/2026-10-02-pr-readiness/README.md) contains the receipts and limits.

Some native hooks update generated documentation timestamps. An update can then require an explicit baseline review. The plugin must not ignore arbitrary source changes to make an update pass. This is a current usability limit.

## Private development capture

The recorder is outside the public plugin package. Its configuration is private under the acceptance home. Its raw event and content files are in `.local/state/lifeos-development-capture/`. The analysis tool rebuilds a searchable index from those files. Raw content stays on the server.

The startup file names the private recorder configuration. Detached hook processes therefore use the same recorder even when systemd starts them with another initial home. The recorder does not change native source files. Historical incomplete traces from the first recorder setup remain as evidence and are separate from the corrected run.

## Services and local-network access

Four user services start on login or boot: the Hermes dashboard, gateway, native acceptance routes, and native PULSE. The account already has systemd linger enabled. The dashboard listens on port 8921. The narrow native acceptance listener uses port 8922. Firewalld admits those ports only from `192.168.8.0/24`.

Native PULSE listens only on `127.0.0.1:8923`. Its full interface is not exposed to the local network because remaining reader governance is open. This acceptance profile has no messaging application credentials. Browser testing does not require Discord.

The unit files are under `/home/lifeos-plugin-install-probe/.config/systemd/user/`. Their names are `lifeos-acceptance-dashboard.service`, `hermes-gateway.service`, `lifeos-acceptance-native.service`, and `lifeos-acceptance-pulse.service`.

To retire the acceptance environment, disable and stop these four units for UID 1007. Remove the two exact runtime and permanent firewalld rich rules for source `192.168.8.0/24` and ports 8921 and 8922. Disable the private recorder or remove its startup file. Preserve the acceptance home and captured data for review. These actions do not require changing the working installations.
