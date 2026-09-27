# Real Hermes patch probe on the isolated account

The first single-query run produced a genuine `patch` call but stopped at a LifeOS review request. Single-query mode had no operator present and denied the request. An interactive rerun allowed the request, then Hermes blocked the write because the fixture was under `~/workspace`, outside `HERMES_WRITE_SAFE_ROOT`. The model had also chosen a single-file replacement instead of the requested multi-file patch.

A third run used `~/HermesWorkspace/hook-parity-probe`, an allowed root, and supplied exact V4A patch arguments in the prompt. The interactive operator allowed the LifeOS review once. Hermes created both files. LifeOS wrote two `tool-activity.jsonl` records for session `20260927_183909_83d97d`, one for `first.txt` and one for `second.txt`. The bridge transcript contains two `Edit` tool uses with paired successful tool results. LifeOS's native `parseTurnEvents` found both edit events and reported `isToolError: false` for each.

The two files did not contain final newline bytes, although the prompt requested them. The Hermes patch result reported success and its diff omitted those bytes. This is a file tool behavior difference in the probe, not evidence that a hook removed the newlines. The probe did not test every installed PostToolUse handler's side effects.
