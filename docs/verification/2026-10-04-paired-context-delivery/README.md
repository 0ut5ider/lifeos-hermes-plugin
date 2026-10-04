# Paired startup context delivery

Date: 2026-10-04. Three cases let actual Claude Code 2.1.272 and Hermes clients reach a real loopback HTTP endpoint after startup. The endpoint returns HTTP 401 for every request. Each client makes one generation request and exits with status one. The runner expects this failure and exits with status zero. No model generates a response.

| Case | Required request content | Result |
| --- | --- | --- |
| `context-delivery-desktop` | The synthetic relationship note, 95 percent wisdom principle, and advisory finding reach the generation request. The 50 percent principle remains absent. | Both clients pass. |
| `context-delivery-remote` | The unmanaged Discord channel environment withholds all four synthetic markers from the generation request. | Both clients pass. |
| `context-delivery-disabled` | Disabled dynamic sources contribute none of the synthetic markers to the generation request. | Both clients pass. |

The [driver](paired-lifecycle-driver.py) uses the same startup fixtures as the preceding [output and state controls](../2026-10-04-paired-startup-effects/README.md). These cases remove the prompt blocker and observe the actual client request. The native client sends an Anthropic Messages request. Hermes sends an OpenAI-compatible chat completion request. The comparison checks source selection and delivery, not equality of the two protocol envelopes. It does not test model reasoning, spoken output, authenticated managed-memory access, or an actual Discord gateway.

[paired-results.json](paired-results.json) retains equal selected outcomes. Each client/case directory records hook input and output, lifecycle events, before and after file contents, command output, request paths, body keys, and original wire-body hashes. [request-proof.json](request-proof.json) records the primary's verification of all six generation requests. The primary decodes the exact retained bytes, checks their hashes, parses them, and verifies the marker assertions against the recorded results.

Raw request bodies remain in mode-0600 files under each disposable `.212` fixture. They are excluded from this public bundle. The public proof records their paths and file hashes. The [runtime manifest](runtime-manifest.json) verifies unchanged Claude Code, Hermes, and plugin sources. The [configuration](configuration.json) records the isolated profiles and commands. Bubblewrap keeps temporary storage private and limits writable filesystem paths to the synthetic home and device mount.

Three assertion tests fail before the delivery cases exist. All 32 focused evidence, trace, and lifecycle tests pass after implementation. A second real run retains exact wire bytes and passes all six client cases again. The cumulative ledger contains 27 equal selected cases for 12 registrations. Complete hook behavior remains open, including other handler branches, full hook groups, generated user responses, and the nine unavailable native dispatch controls.

Active `.212` services, installed product code, and memory ownership settings remain unchanged. The combined release remains staged, with voice after the core features.
