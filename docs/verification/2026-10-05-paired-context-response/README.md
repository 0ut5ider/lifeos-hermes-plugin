# Paired startup context and successful responses

Date: 2026-10-05. Three cases run actual Claude Code 2.1.272 and prepared Hermes clients against the configured private FlashNext gateway. All six main requests return HTTP 200. Both clients exit with status zero and deliver `READY` in their final result.

| Case | Required effect | Result |
| --- | --- | --- |
| `context-response-desktop` | Relationship context, the 95 percent wisdom principle, and the advisory finding reach the model. The 50 percent principle remains absent. | Both clients pass and deliver a response. |
| `context-response-remote` | The unmanaged Discord environment withholds all four synthetic context markers. | Both clients pass and deliver a response. |
| `context-response-disabled` | Disabled dynamic sources contribute none of the synthetic context markers. | Both clients pass and deliver a response. |

The [driver](paired-lifecycle-driver.py) runs the selected native hook through each client's real startup event. The [relay](paired-response-server.py) records exact request and response bytes privately, substitutes the configured private model identifier, and forwards each main request to the gateway. It preserves the native client's `?beta=true` query. It supplies the private credential without recording authorization headers. The gateway generates the response; the relay supplies no scripted model answer.

[final/paired-results.json](final/paired-results.json) retains equal selected state and delivery outcomes. [final/request-proof.json](final/request-proof.json) records verification of all six exact request bodies, response-body hashes, context assertions, and final client results. The original body records remain in mode-0600 files outside this public bundle. The retained client directories contain synthetic hook input and output, lifecycle events, file state, and command output.

[final/runtime-check.json](final/runtime-check.json) verifies 16,925 staged source files against the [runtime manifest](runtime-manifest.json). It also records the native executable, trace driver, and candidate fixture hashes. The manifest excludes dependency directories. These cases use the prepared dependencies; they do not establish a clean dependency installation. The [final configuration](final/configuration.json) identifies each isolated home and command. Bubblewrap limits writable paths to the synthetic home and device mount and gives each client a private temporary directory.

The [first run](failed-first-run.json) fails all three pairs. Its relay rejects `/v1/messages?beta=true` before the gateway receives the native request. Hermes completes each main turn, then makes a separate title-generation request. One title request returns HTTP 500. The corrected fixture disables the supported title model upgrade only in the disposable response profiles. Auxiliary title generation and its model routing remain unverified here. Production settings and the four tier mappings remain unchanged.

The second run passes all three pairs but logs a recorder startup warning. The reused interpreter loads a development recorder through a Python startup file that pins a different account root. Bubblewrap prevents its write outside the synthetic home. The final run uses a separate interpreter copy without `lifeos_development_capture.pth`; it changes no installed interpreter or recorder settings. All six final clients pass without that warning. The top-level client artifacts retain the second run, and `final/` retains the clean third run. The ledger uses the final result.

The three response assertion tests fail before these cases exist. A separate HTTP transport regression fails with expected status 200 and actual status 401 before query handling is corrected. All 38 final lifecycle, evidence, inventory, trace, and transport tests pass afterward. The transport test uses a local HTTP peer to verify relay behavior; the six actual client runs provide the model-response evidence.

This comparison covers selected unmanaged startup context and a successful main response. It does not verify all hook branches, complete installed hook groups, authenticated managed-memory admission, an actual Discord gateway, title generation, or voice. The cumulative ledger contains 30 equal selected cases for 12 registrations. The completion gate remains open.

Active `.212` services, installed product code, and ownership settings remain unchanged. The combined release stays staged.
