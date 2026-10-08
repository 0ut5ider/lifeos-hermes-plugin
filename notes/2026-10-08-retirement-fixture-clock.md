# Retirement fixtures and filesystem clock order

Date: 2026-10-08.

The 265-case Life source-review adjacent gate has one intermittent Work failure. Its fixture forgets a synthetic session, touches the retained source files with os.utime(path, None), then expects an unrelated project to remain visible. The expectation requires source timestamps later than the retirement cutoff.

The first observer attaches to the parent memory object and receives no observations because admission runs in another process. A parent retirement readback then passes 30 runs. A lower-impact clock observer passes 40 runs. Neither result establishes the failing path. The direct kernel probe records one noncurrent timestamp in 10,000 touches, 9,539 nanoseconds before the preceding clock sample.

The final observer adds no work before the tested operation. It reads source and retirement timestamps only after a failed HTTP response. Two of 50 actual Work runs fail. All three refreshed sources are 24 microseconds older than retirement in one run and 550 microseconds older in the other. The policy correctly excludes the sources. Instrumentation that adds a database read before the touch can obscure the failure.

The fixtures now supply time.time_ns() explicitly to os.utime. They still use current wall-clock values. No future timestamps, sleeps, source approvals, or policy changes are introduced. Finance and Business have the same fixture assumption, so their retirement fixtures receive the same correction. The raw probes and first failing gate remain in the verification directory.
