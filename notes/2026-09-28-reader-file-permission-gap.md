# Reader command operands bypass file rules

Date: 2026-09-28. The isolated Claude Code 2.1.272 reference account on `.212` used its private local model to run `cat parity-file` from a disposable `.claude` directory. A matching `Bash(cat parity-file)` allow produced zero permission denials and read the file. Adding `Read(./parity-file)` to the deny list produced one denial and did not return the file marker. The reference probe removed the file.

The plugin's `HookBridge.command_approval` returned no block for the same command and rules. Its Bash target parser recognized redirects and `tee` outputs but did not recognize file operands. This was an authorization bypass. The failing regression returned `None` instead of `{"action":"deny"}` before the parser change.

The parser now finds literal operands of `cat`, `head`, and `tail`, and the file operands and script files of `sed`. It follows recognized Bash wrappers such as `timeout`. Unknown options and dynamic arguments request review. Every `sed` invocation requests review when no file rule denies it, because a sed script can open additional files through its own commands. The local suite passed 270 tests with 64 optional skips. The `.212` source suite passed 270 tests with 53 optional skips. This fixes the measured `cat` bypass; the other reader forms have bridge tests, not separate Claude Code reference probes.

The first local full-suite run failed seven unrelated project-hook tests. An empty `/tmp/.git` directory made the fallback project detector classify `/tmp` as the project root for its temporary projects. Running the suite with `TMPDIR=/var/tmp/lifeos-bridge-suite` passed all tests. The directory was left untouched. This test environment issue should not be mistaken for a hook regression.
