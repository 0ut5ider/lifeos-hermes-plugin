# Generated memory needs checks after request conversion

Date: 2026-09-30

The first prompt guard checked system roles and the installed SOUL file. Independent SDK probes found three gaps: tuple and lazy inputs, `extra_body` overrides, and compression that turned a cached system message into a user message. The corrected callback checks the effective request body and treats trusted compression inputs as generated context.

Two closure reviews found additional Responses representations. Plain string `input` sent one request with a removed claim. A `function_call_output` item also sent one request because its text was in `output`, not `content`. The reproduction used real required middleware and the installed OpenAI SDK against an isolated HTTP server. It did not prove full agent rotation reachability.

The compression guard now traverses materialized input fields and decoded JSON arguments. It refuses uninspectable inputs and excessive nesting. Primary user quotes retain their separate rule. The third independent review passes 52 focused tests and finds no further material issue in the bounded unit. This is a conservative refusal, not automatic history rebuilding or semantic recognition of every paraphrase.

An unrelated native startup test found that the desktop-only guard skipped approved relationship context in both synthetic messaging apps. A managed connector now delegates each dynamic source to its permission check. Unmanaged remote sessions retain their native isolation. Missing, unknown, and restricted contexts do not receive the synthetic relationship marker. Restricted static prompts and actual delivery remain separate gates.

The complete regression executes 582 tests with 505 passes and 77 skips. The subsequent closure includes one additional nesting test collected after the full run started. A primary archived-probe run initially used an interpreter without `ruamel.yaml`. Its import failures are preserved separately and do not count as policy denial. The corrected runner uses the complete declared dependency environment and requires the expected policy error plus zero requests.
