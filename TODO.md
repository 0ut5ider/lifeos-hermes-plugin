# Project todos

The [0.7.3 release record](docs/verification/2026-10-16-release-0.7.3/README.md) is the current qualification and deployment reference. The [changelog](CHANGELOG.md) records delivered features. The [historical TODO snapshot](docs/history/2026-10-16-todo.md) preserves completed milestones and their original evidence links.

## Documentation audit follow-ups

- [x] Synchronize `hermes-session-lifecycle.patch` between development and distributed copies. On 2026-10-17 the development copy in `patches/` was replaced with the canonical copy in `lifeos_hook_bridge/patches/`, and `tests/test_patch_bundle.py` passes.
- [ ] Add and verify an explicit dashboard ownership-activation path for a genuinely empty or no-import review. The current UI hides **Review publication plan** when there are no decisions. Do not require unwanted imports or manual journal edits. See the [current activation path and limit](docs/installation-workflow.md#choose-memory-ownership-separately).

## Deferred product work

- [ ] Decide and implement installing LifeOS again after a verified removal. Removal retains the native data and the removal selection, and preparation refuses both. See the [design limit](docs/in-place-installation-design.md#8-host-record-updates-and-removal).

- [ ] Complete Discord voice input and spoken replies. Verify transcription, speech generation, and actual Discord delivery before enabling daily voice.
- [ ] Add native Content audio and video processing with the voice release. Verify extraction, transcription, runner control, and actual media outputs.

## Installation redesign

The accepted [in-place installation plan](docs/in-place-installation-plan.md) supersedes the private-runtime recommendation in the architecture review. The installer must preserve the existing Hermes installation and refuse unsupported hosts. Complete and qualify these steps as one release:

- [x] Add the read-only compatibility detector, manifest generator, `hermes lifeos-release compatibility`, and the dashboard result. See the [host compatibility record](docs/verification/2026-10-17-host-compatibility/README.md).
- [x] Gate the in-place **Install LifeOS** action on a compatible result, and repeat the check under the installation lock before any change.
- [x] Add pinned LifeOS component acquisition and verified cache reuse.
- [x] Add durable in-place patch transactions and coordinated consumer restart.
- [x] Add qualified patch updates, Hermes updater coordination, and original-file restoration.
- [ ] Qualify real dashboard installation, recovery, and removal with existing tools and plugins, including the managed-release transition. The [in-place qualification record](docs/verification/2026-10-17-inplace-e2e/README.md) covers these flows on containers through the release manager functions and a loopback release server. On 2026-10-18 the published `v0.8.0-rc.1` passed the GitHub plugin URL (command line with `--ref`) and the dashboard install, return, and removal buttons on a container; that record lists eight findings. The Plugins page URL install waits for the merge to `main`.
- [ ] Complete independent review and exact-release qualification before daily deployment. The development host runs `0.8.0-rc.4` in place since 2026-10-18 ([record](docs/verification/2026-10-18-dev-inplace-transition/README.md)).
- [x] Fix the findings of the 0.8.0-rc.1 dashboard test. 0.8.0-rc.4 passed the dashboard install, return, and removal on a container without a recovery.
- [x] Rehearse the daily host layout on a container before daily moves. A clone of daily moved to `0.8.0-rc.4` and back; the HTTP memory connections, grants, and tokens survive ([record](docs/verification/2026-10-19-daily-rehearsal/README.md)).
- [ ] Decide the proposed reinstall after removal (design section 8).

## Completed capabilities with canonical references

| Capability | Reference |
| --- | --- |
| Code cleanup and contributor navigation | [0.7.3 release](docs/verification/2026-10-16-release-0.7.3/README.md) |
| Installation and complete updates from Hermes | [Installation workflow](docs/installation-workflow.md) |
| Hook compatibility acceptance | [Step 1 ledger](docs/parity/step1-acceptance.md) |
| Memory import, reverse export, provider return, and software removal | [Portability guide](docs/memory-portability.md) |
| HTTP memory MCP and owner-approved external connections | [HTTP guide](docs/http-memory-mcp.md) |
| Governed Pulse core-file editor and Atlas retention | [0.5.0 release](docs/verification/2026-10-14-release-0.5.0/README.md), [Atlas retention](docs/verification/2026-10-11-atlas-retention/README.md) |
| Notification-first Discord admission correction | [0.7.1 release](docs/verification/2026-10-16-release-0.7.1/README.md) |
| Setup interface styles, sections, and accessible controls | [0.7.2 release](docs/verification/2026-10-16-release-0.7.2/README.md) |

New Hermes and LifeOS upstream versions require a port and qualification under the [update policy](docs/update-policy.md). A clean patch application alone does not establish compatibility.
