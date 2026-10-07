# The asynchronous timeout hypothesis does not justify a fix

Date: 2026-10-05. A real local asynchronous hook declares a one-second timeout, sleeps for two seconds, and creates its completion marker after 2.132 seconds. The bridge does not copy the timeout into the local detached runner request. That initially looks like a missing deadline.

The current [official Claude Code hook reference](https://code.claude.com/docs/en/hooks#configure-an-async-hook), checked on October 5, states that `async: true` hooks do not receive timeout enforcement after background execution starts. It separately states that headless sessions cancel running asynchronous hooks at teardown. The observed local behavior therefore does not establish a deadline compatibility defect. Adding a timeout at this point would change the native contract without evidence.

The next measurements target output delivery and teardown. A successful short hook proves its final effect, not cancellation behavior or delivery into the first model request. No product change follows this hypothesis.
