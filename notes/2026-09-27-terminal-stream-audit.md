# Terminal stream audit

Date: 2026-09-27

Hermes's local environment starts foreground processes with `stderr=subprocess.STDOUT`. The terminal tool therefore receives a single `output` value. Once those streams merge, the bridge cannot reconstruct their origin.

The installed `.212` LifeOS hooks were searched for both `tool_response` and stdout or stderr references. AgentInvocation stringifies the whole response, LoopDetector only declares the response field, and Safety stringifies it for annotation. EventLogger is the one hook that reads terminal stream fields. Its installed compatibility patch accepts Hermes's combined `output` and records that value as an output preview. A separate native probe already verified that patched logger with a synthetic terminal result.

Separate stdout and stderr would require a Hermes environment and terminal-result change across backends. The current installed LifeOS hooks do not require that change for their observed effect. A future hook that interprets one stream differently from the other would.
