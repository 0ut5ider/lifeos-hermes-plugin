# Explicit LifeOS deny in approval bypass mode

The first Hermes bypass implementation returned approval before calling the plugin policy hook. That made a LifeOS `permissions.deny` rule ineffective when Hermes approval mode was `off` or yolo. The observed failing case used an exact Bash deny and the installed LifeOS Safety hook.

A paired Claude Code probe supplied a control. Its `bypassPermissions` mode still blocked the exact deny, with no file effect. Without the rule, the command executed and `PermissionRequest` did not run. The default mode requested permission for the neutral command in the headless probe.

The generic Hermes patch moves the plugin decision ahead of the bypass approval. The bridge checks explicit LifeOS rules before abstaining in bypass mode. A test with the real installed Safety hook now denies the exact command in both Hermes bypass modes. A neutral command approves without invoking that hook. Hermes hardline checks still run first.

This fixes one ordering mismatch. It does not prove the behavior of every Claude Code rule source or an interactive approval path. The patched host source has not been restarted into the live `.212` Discord gateway. It remains part of the staged test branch.
