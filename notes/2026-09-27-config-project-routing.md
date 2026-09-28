# 2026-09-27: ConfigChange routing in a session with two projects

The bridge already filtered a project settings change to sessions that had visited that project. A separate lookup chose which project's hook registrations to run from the event's `cwd`. The watcher thread supplied its own working directory, so a session with two projects had no matching project for the event.

A regression test registered project A and project B in one session, then changed A's settings. Before the fix, A's project `ConfigChange` hook did not run. The bridge now supplies A's root as the event working directory. The test confirms A's hook runs and receives A's `cwd`, while B's hook does not run.
