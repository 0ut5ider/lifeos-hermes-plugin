# Local owner jobs

Date: 2026-10-08. Native sources use the prepared Knowledge command candidate.

The candidate exposes `hermes lifeos-job memory-consolidation` and `hermes lifeos-job proposal-gc`. The first job runs native session harvesting for the 20 most recent admitted sessions, then weekly rating synthesis. The second job runs native automatic proposal cleanup. The command accepts no arbitrary program or arguments.

The job admits the current operating-system account as `terminal:<uid>` at the selected Hermes profile. The memory configuration must bind that account to the owner and grant unrestricted owner reads and writes. Ownership must already be active. The command cannot create its own grant or fall back to unmanaged native operations.

The command resolves the current Hermes provider route and reads the existing plugin tier settings. Native child processes receive the selected LifeOS home, the admitted context, and the unchanged tier mapping. The command removes inherited Discord and cron metadata. Each invocation has its own admission. Native publication retains its current source and policy checks.

The command captures output privately until current authority and retained-content checks permit delivery. A policy revocation after a completed native write withholds output and preserves the committed learning. The command sets a maximum deadline of 540 seconds. On a process timeout or interruption, it kills the native process group.

The [feature baseline](owner-jobs-before.txt) records the missing owner-job module. The [first native run](owner-jobs-first.txt) passes seven of eight checks. The transcript fixture initially has an admission from before the local grant changed the policy signature. The native collector correctly skips that transcript. The corrected fixture captures its synthetic foreground admission under the final policy. The [next run](owner-jobs-second.txt) passes all eight checks.

The [command baseline](owner-job-command-before.txt) records the missing Hermes command. The [command gate](owner-job-command-first.txt) passes three cases through actual plugin discovery and the command parser. The command publishes a private weekly synthesis and refuses disabled ownership and an arbitrary job name.

The [final adjacent gate](owner-jobs-final.txt) passes 76 tests in 27.641 seconds with warnings treated as errors. It includes the owner job tests, command tests, session consolidation, proposal cleanup, runtime admission, and native response authority. A separate process observes actual native execution for inherited metadata replacement and post-commit revocation. These cases use no substituted native program or model call.

The [process lifetime gate](processes.txt) passes two additional checks. A real subprocess starts a grandchild. Both a deadline and SIGTERM stop the child and grandchild. The gate treats a killed grandchild awaiting the operating system's reaper as stopped.

This gate verifies the selected deterministic jobs. It does not verify the installed Pulse scheduler, live private FlashNext requests from background inference, or an active daily profile. Installed job activation and combined release acceptance remain open. The private model and effort settings remain unchanged.
