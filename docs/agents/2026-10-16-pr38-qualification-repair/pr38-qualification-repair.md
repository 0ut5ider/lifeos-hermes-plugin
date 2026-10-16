# PR38 qualification repair

Date: 2026-10-16. Role: primary agent. Model: GPT-6.1 Sol.

The first exact-archive run executes 1,128 tests. It passes 1,123 cases, reports three errors, and reports two failures. Both health fixture errors report `OSError: [Errno 122] Disk quota exceeded`. The reviewer exports and this run overlap on the workstation temporary filesystem. The process-inspection failure and error reproduce the existing account boundary limit. All eight related cases pass under the disposable service account.

The remaining deadline test reads the grandchild process state immediately after the direct child exits. A real-process probe repeats the existing termination function 100 times. Twelve grandchildren are nonterminal at return. All reach a terminal state within five seconds. The raw samples record exact transition times. This establishes that waiting for the direct child does not wait for every grandchild state transition.

The test assertion now polls for at most five seconds. It accepts an absent process or a zombie state. It also handles a process that disappears during the procfs read. A new real-process regression fails before the assertion change and passes afterward. A mutation kills only the direct child. The revised assertion detects the surviving grandchild and the mutation operator cleans up its owned group. Product cancellation code is unchanged.

All 16 health and process module cases pass on replay. One initial replay misses a fixture variable; the corrected replay includes it. The initial failed run and both replays remain in the compressed evidence. A second complete archive run uses a private temporary directory on the larger cache filesystem. It must finish before qualification.
