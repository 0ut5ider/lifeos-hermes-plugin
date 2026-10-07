# Observer history under parallel callbacks

Date: 2026-10-06. Scope: Step 1 observer and audit controls.

Sixteen callbacks for one session ran with eight worker threads. Each callback started the actual installed `PostToolObserver` program. Before coordination, the saved counter and window both contained twelve entries. The callbacks had distinct signatures, so deduplication did not explain the loss. The native read-modify-write state updates overlapped.

The bridge now coordinates recognized native post-hook programs with an owner-only advisory lock for the session. The operating system releases the lock after interruption. Tests with separate processes prove release after process death and concurrent progress for another session. Independent hook programs still run in parallel. The final native observer counter, window, and distinct signature count are sixteen.

The lock applies to synchronous installed state hooks. Detached append-only EventLogger processes use their existing execution path. Twenty-four rows survive both normal bridge closure and abrupt parent death. These controls measure actual child processes and parse every JSON row. They do not claim Discord delivery.

Audit reconciliation has two independent debounce checks. EventLogger checks the state file modification time. WorkReconcile checks its saved `checkedAt` timestamp. A fixture that ages only the modification time correctly starts a child that exits without another sweep. The control ages both synthetic values before testing an actual shell mutation and detached reconciliation.
