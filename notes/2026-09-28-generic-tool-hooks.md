# Generic Hermes tool hooks and web extraction

On 2026-09-28, I checked whether the bridge sent Hermes tools outside its fixed Claude Code name map to the installed LifeOS hooks. It did not. The bridge returned before `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, and transcript recording for those tools. A regression test using `todo_list` failed because the hook output file did not exist.

The bridge now keeps an unmapped Hermes tool name. Generic LifeOS hook groups receive its tool calls and results, and the bridge records them in the transcript. The explicit Claude Code name mappings remain. A separate regression test showed that Hermes `web_extract` did not match LifeOS's `WebFetch` Safety registration. The bridge now maps `web_extract` to `WebFetch`.

On the isolated `.212` account, 109 tests passed with the patched LifeOS checkout and Bun available. A direct bridge probe called the installed `Safety.hook.ts` with a synthetic `web_extract` result. It returned the external-content warning and produced two transcript rows with a `WebFetch` tool use. No network fetch ran in that probe. The installed bridge file has the same SHA-256 digest as the tested source, and the restarted dashboard returned HTTP 200 at `192.168.8.212:9119/api/status`.

This verifies the generic dispatch path and one native safety effect. It does not establish behavioral parity for every Hermes tool schema or every LifeOS hook. Hooks that require a specific Claude Code tool name still need a deliberate mapping and a payload check.
