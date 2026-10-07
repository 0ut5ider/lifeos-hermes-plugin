# Distill reservation refusal

2026-10-04. A marking operation can reject publication and still lose a later state edit during recovery. The initial focused marking gate passes 21 tests, including an actual exit 73 and conflicts before reservation. A probe then inserts a real later edit and account revocation immediately after the journal captures its recovery copy.

The service returns refusal. Its unhandled authority exception leaves the journal outcome unknown. The next owner read restores the old copy and removes the later edit. One unchanged probe reproduces this loss. The correction converts validation failures before publication into a committed conflict receipt. Recovery then discards the unused copy and preserves the edit. Actual process death after publication retains the unknown outcome and restores the previous bytes.

The original-native comparison also finds a format mismatch: the service writes compact JSON while the native command writes indented JSON. The broad gate has one failure and 205 passes. State values and counters match. The final correction uses the native indentation and retains the absence of a final newline. The final correction passes 25 tests and two subtests. Fourteen native controls pass, including exact state-byte equality. No server changes occur.
