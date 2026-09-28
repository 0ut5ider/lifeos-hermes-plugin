# Safety authority for LifeOS grants

Adrian chose Hermes's hardline denial as the final authority on 2026-09-28. A native LifeOS `PermissionRequest` grant may approve a recoverable Hermes prompt, but it cannot override a hardline command block. User deny rules and Tirith warnings also retain their existing authority. This keeps one unconditional boundary for commands that Hermes classifies as catastrophic, even if a LifeOS hook is wrong or its input was shaped unexpectedly.

The current Hermes approval path checks hardline rules before plugin grants. An isolated `.212` probe previously showed LifeOS granting a synthetic `/tmp` removal while Hermes still blocked `rm -rf /`. This decision records the intended behavior; it does not authorize a new bypass. The [hook parity record](../docs/hook-parity.md) describes the other approval cases.
