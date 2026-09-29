# Approval mode reference probe

Date: 2026-09-28. Role: native reference investigator. Question: Does Claude Code bypass mode ignore an explicit Bash deny, and does it run `PermissionRequest` without a rule? Model: Claude Code 2.1.272 routed to the private `flashnext-w4a16-fp8ple` model.

The [probe](probe.py) ran in the isolated `lifeos-claude-ref` account on `.212`. It installed disposable `PreToolUse`, `PermissionRequest`, and `PostToolUse` event recorders in a temporary settings file. Each case asked for one exact Bash command that would create a temporary marker. The probe recorded the event sequence, final permission denial, and marker effect. [Raw results](results.jsonl) contain all four cases.

| Permission mode | Exact deny rule | Hook events | Marker | Result |
| --- | --- | --- | --- | --- |
| default | yes | PreToolUse | absent | denied |
| bypassPermissions | yes | PreToolUse | absent | denied |
| bypassPermissions | no | PreToolUse, PostToolUse | present | executed |
| default | no | PreToolUse, PermissionRequest | absent | headless approval unavailable |

The observed rule is narrow: bypass skips an approval request but does not cancel an explicit settings deny. The probe does not cover project trust, managed settings, rule changes during a turn, file and Model Context Protocol tools, or an interactive approval UI. Claude Code printed an `unrecognized_model` warning for the local model, but the tool events and file effects were recorded. No result depends on the wording of the model's final answer.

The matching Hermes change is [the bypass policy patch](../../../patches/hermes-bypass-policy.patch). It passes bypass state into `pre_command_approval` after Hermes hardline checks and before normal approval shortcuts. The bridge checks LifeOS file and Bash rules first, then skips `PermissionRequest` when bypass is active. The real installed Safety hook test covers exact denial in Hermes `off` and yolo modes, and confirms that a neutral bypass command does not run `PermissionRequest`. The focused host approval suite passed 59 tests; the full plugin suite passed 308 tests with 55 optional skips.
