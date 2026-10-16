# 2026-10-16: waiting for a leader does not wait for its process group

The 0.7.3 archive run exposes a racy cancellation test. After SIGKILL reaches the group and `wait()` returns for its leader, the grandchild can still have a nonterminal procfs state. A 100-run probe observes this in 12 runs. Every observed grandchild then reaches a terminal state within five seconds. The test now polls within a fixed five-second bound. A parent-only kill mutation still fails because its grandchild survives. No product cancellation code changes.

The same qualification run reports two explicit disk-quota errors while building synthetic health fixtures. Concurrent source exports put pressure on the workstation temporary filesystem. Future full qualification runs use a private directory on the larger cache filesystem. Preserve failed attempts and correct missing fixture variables before interpreting a replay.
