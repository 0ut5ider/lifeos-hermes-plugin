# Restore boundaries found by the correction review

Date: 2026-10-02

The first correction suite passed 349 cases, but a second reviewer reproduced three restore failures. An actual profile on `/dev/shm` could not rename its files into an update snapshot on `/tmp`. The failure occurred after the LifeOS program swap. Repeating recovery produced the same `EXDEV` error. A separate profile edit after the program rename reached a content guard too late for safe refusal. Both paths stopped the gateway without restarting it.

The worker then wrote `failed`, while the transaction still said `restoring`. The authenticated recovery route required `interrupted` and returned HTTP 409. Passing transaction tests had not checked this error mapping. The primary reproduced all three results. Four added tests failed with eight failures and two errors across their subcases before correction.

Retained files now move into private directories beside their targets. An index in the update snapshot records each destination before its rename. This keeps the move atomic across the supported layout without an unsafe copy-and-delete fallback. The profile checks run before the program swap. Later writes remain in the archive. An unfinished swap stays recoverable through the worker status. These corrections have local transaction and authenticated route tests, plus an actual process-kill test. They do not establish live service or power-loss acceptance.

The next review confirms eight process-kill boundaries and finds an inherited recovery request-admission gap. Adding the existing guard fixes admission but changes the endpoint to asynchronous execution. That exposes a scheduling regression: a concurrent HTTP request takes 817 milliseconds during a captured 0.8-second launch. The parent handles it in 1.9 milliseconds. The primary repeats the result and adds a failing scheduling test. Moving the synchronous recovery sequence into the existing thread pool produces a 5-millisecond response while launch still waits. All 25 affected dashboard tests and 32 real local HTTP cases pass. These timings isolate scheduling; they do not measure real systemd launch duration.
