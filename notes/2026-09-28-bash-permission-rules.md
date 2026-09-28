# Bash permission rule timing

Date: 2026-09-28. Claude Code 2.1.272 ran in the isolated `.212` reference account against the private local model. Each probe registered Bash `PreToolUse` and `PermissionRequest` hooks. The permission hook denied its own event. No `--allowedTools Bash` flag was used.

| Setting | Command | Observed events |
| --- | --- | --- |
| `ask: ["Bash(pwd)"]` | `pwd` | `PreToolUse`, `PermissionRequest` |
| `allow: ["Bash(curl -I --max-time 1 http://192.168.8.1:9)"]` | matching curl | `PreToolUse` only |
| `deny: ["Bash(curl -I --max-time 1 http://192.168.8.1:9)"]` | matching curl | `PreToolUse` only; Claude reported permission denied |

The bridge now applies literal Bash `deny`, `ask`, and `allow` rules in that order for local user and trusted project settings. An exact deny blocks without running the native PermissionRequest hook. An exact allow skips that hook but does not override Hermes's hardline or Tirith decision. A matching ask runs the hook or requests human review if there is no hook. Unrelated literal rules no longer cause a probed read-only command to fire PermissionRequest. Local settings are refreshed immediately before command approval, so a changed allow rule cannot remain active until the background watcher polls.

The patched `.212` Hermes guard test used the installed LifeOS `Safety.hook.ts`. An exact curl allow produced no native permission decision, but Tirith still requested review for the raw-IP HTTP URL. Changing the same setting to an exact deny blocked without another prompt. The full plugin suite passed 215 tests with 53 optional fixture skips.

This is a limited permission evaluator. Wildcard patterns, compound-command splitting, wrappers, parameter rules, managed settings, and remote project permission rules are not fully interpreted. Uncertain deny or ask patterns prevent an automatic allow and request review. A human review is still weaker than a Claude Code deny rule because the human can approve it. Full rule parity remains open.
