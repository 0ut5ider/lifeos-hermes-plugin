# 2026-09-27: Permission grants crossed two approval systems

LifeOS's `Safety.hook.ts` treats `rm -rf /tmp/lifeos-bridge-synthetic-never-created` as a safe command shape and returns an explicit allow decision. Hermes classifies the same string as `delete in root path` and requests approval. The mismatch showed why forwarding only `PreToolUse` hooks could not preserve LifeOS permission behavior.

The first generic approval callback passed its focused tests but broke 6 of 55 related tests. The tests that failed observed an extra callback in smart approval mode, including one that requires approval observers to receive redacted content. The contract was narrowed to Hermes manual approval mode, after hardline and user deny checks. A separate Tirith finding still reaches the human gate. A plugin deny beats another plugin's allow. The combined focused approval suite now has 107 passing tests.

The installed native LifeOS hook then granted the synthetic `/tmp` command through the real plugin loader. It abstained on `sudo systemctl restart example.service`, which Hermes denied through the normal callback. Hermes blocked `rm -rf /` at its hardline floor. No sample command was executed. This verifies Bash command approval in the test fixture, not Write, Edit, or MCP permission parity.
