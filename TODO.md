# Project todos

The [0.7.3 release record](docs/verification/2026-10-16-release-0.7.3/README.md) is the current qualification and deployment reference. The [changelog](CHANGELOG.md) records delivered features. The [historical TODO snapshot](docs/history/2026-10-16-todo.md) preserves completed milestones and their original evidence links.

## Documentation audit follow-ups

- [ ] Synchronize `hermes-session-lifecycle.patch` between development and distributed copies, then verify both preparation paths produce the same intended source. The current development copy lacks the distributed Discord mirror-policy and webhook-threading changes. See the [source preparation limit](docs/clean-install.md).
- [ ] Add and verify an explicit dashboard ownership-activation path for a genuinely empty or no-import review. The current UI hides **Review publication plan** when there are no decisions. Do not require unwanted imports or manual journal edits. See the [current activation path and limit](docs/installation-workflow.md#choose-memory-ownership-separately).

## Deferred product work

- [ ] Complete Discord voice input and spoken replies. Verify transcription, speech generation, and actual Discord delivery before enabling daily voice.
- [ ] Add native Content audio and video processing with the voice release. Verify extraction, transcription, runner control, and actual media outputs.

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
