# Agent carrier observation

The original paired PreToolUse run logged an inherited model on Hermes while Claude Code logged its session carrier. The hook reads the assistant transcript. Claude Code writes the tool call before this hook; Hermes writes it after execution.

The first host-field attempt used the request observer. A real probe confirmed three observations with distinct parent and child session IDs. Each observation named the requested alias, `lifecycle-fixture`. The next paired run still disagreed: the native hook recorded the served model, `flashnext-w4a16-fp8ple`. The requested alias cannot answer which model served the turn.

The bridge now uses the successful response observer. The inherited and explicit Opus cases pass on all four clients. Their comparison retains model, level, agent type, and parent identity. The focused suite passes 298 tests, with one optional test skipped. This establishes selected start behavior, not complete delegation compatibility.

The instrumentation initially wrote outside the fixture home. Bubblewrap makes that part of the filesystem read-only. A callback failed silently, and a registration-time write prevented plugin registration. Moving the capture into the writable fixture home proved that the intended plugin loaded. Future isolated probes must verify their loaded source and writable output path before accepting an empty capture.
