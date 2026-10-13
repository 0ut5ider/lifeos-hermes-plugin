# 2026-10-13: Unchanged publication can invalidate service recovery

The sealed `e5a6ccf1` candidate passes 658 integration tests and 716 native Hermes tests. Its real guest recovery still fails after termination at `programs-published`. The dashboard stays stopped, its definition bytes match the admitted bytes, and systemd reports `NeedDaemonReload=yes`.

A real user-service control separates two causes. Adding an inactive unit leaves the existing unit's flag at `no`. Atomically publishing the same definition bytes changes the inode and changes the flag to `yes`. The program transaction rewrites every reviewed file, including the unchanged stock dashboard definition.

The first service fixture did not reproduce the failure. Its inactive linked unit can be reloaded after systemd releases it. Enabling the synthetic unit under `default.target` retains the loaded unit and reproduces the guest's recovery refusal. The test uses real processes, a real program transaction, and the actual user service manager.

The correction skips publication of a file when its admitted before and after fingerprints are equal. Preparation still checks source, staged copy, and target. The journal retains the entry. Changed files still publish, and recovery still refuses changed service definitions. No service check accepts stale manager properties.

The failed guest and safe observer receipt remain diagnostic evidence. The candidate remains unpublished. A new sealed candidate must repeat the guest interruption and preserve the later synthetic user file before qualification.
