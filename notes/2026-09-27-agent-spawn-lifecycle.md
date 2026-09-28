# Background Agent lifecycle probe

Date: 2026-09-27

The installed LifeOS `AgentInvocation` hook identifies an asynchronous Agent response by matching a spawn acknowledgment phrase in `tool_response`. Hermes instead returns a JSON object with `status: dispatched` and `mode: background`. The bridge passed that object to LifeOS unchanged. On the isolated `.212` account, the native hook logged `subagent_start` and an immediate `subagent_stop` for a synthetic background dispatch. The child had only been accepted, so that stop record was false.

A regression test first showed that the bridge passed the JSON object to the hook. The bridge now recognizes Hermes's dispatched background handle and presents a spawn acknowledgment string containing the JSON to the Agent PostToolUse hook. It keeps the original JSON result in the private transcript and in Hermes's own tool result. The native probe then logged `subagent_start` and `subagent_spawned_async` under a temporary LifeOS root. The full local suite passed 75 tests, with four optional native skips.

This adapter applies only to a successful Agent PostToolUse event whose parsed result declares both `status: dispatched` and `mode: background`. Foreground and failed Agent results keep their original hook response.
