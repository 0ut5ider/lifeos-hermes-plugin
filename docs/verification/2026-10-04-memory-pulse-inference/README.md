# Native PULSE adapter inference

Date: 2026-10-04. Five controls run the native adapter, installed Inference.ts, shipped Claude command shim, tier resolver, direct child program, memory runtime, and local HTTP server. The server returns declared synthetic page content. No model result or native process result is replaced.

The [corrected gate](candidate-output.txt) passes five tests in 23.85 seconds. The [recorder](controls-output.txt) passes the same five controls and saves [actual requests and outcomes](native-outcomes/). The request reaches `/v1/messages` with `synthetic-flashnext` and low effort. The native schema accepts the response, the adapter publishes its page and metadata, and the next call uses the cache without another request.

An unapproved child route and a private source make no HTTP request. A source edit or account revocation during the actual request prevents page publication. The source-change response is sanitized by the native connector. The [first run](before-output.txt) fails only because its assertion expects the internal source-conflict message; four controls pass. The corrected assertion requires the observed connector refusal. No product change is needed for these five controls.

The [command](candidate-command.json) records the tested sources. All hashes match. The native distribution and patch copies remain unchanged. Dependencies come from the preceding distributed adapter fixture. No running server changes occur, and ownership remains disabled outside the synthetic fixture.

The local server supplies a scripted response. These results establish request assembly, admission, native validation, publication, and cache behavior. They do not establish private FlashNext generation quality, live provider availability, all four tier routes, source-change prevention between the final input check and transport, or a complete adapter output transaction. DerivedSync child acceptance and combined service recovery remain separate gates.
