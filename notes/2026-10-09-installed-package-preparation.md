# Installed daily package preparation, October 9, 2026

The two local capture units are committed as b3209502 and 581d76a7. The canonical current package validates on .252. Its dependency inputs match the installed runtime exactly, and Bun is 1.3.14 on both the harness and .252. Full local fresh-store tests pass two cases in 20.535 seconds.

The isolated remote installation and named fresh-store preparation complete in 31.515 seconds. The signed result retains Adrian and Cerebo and zero active facts. Ownership and sharing remain disabled. No services start. Main gateway, dashboard, and Pulse remain active with the previous configuration and paths.

Two orchestration defects require explicit preservation. Package preparation initially runs before the clean Git worktree finishes and the source-cleanliness guard refuses. Waiting for completion and clean status fixes the ordering. The remote nested shell launcher writes n 0 instead of a numeric completion marker. Preserve its exact bytes. An independent FreshStore.review_home call validates the signed final review and current owner binding. Do not recast the damaged marker as proof of an exit code. Future launchers use a written file or a Python subprocess wrapper with explicit status recording.

The staged package and generated fixture store remain under the October 9 migration directory. No live memory records or transport credentials are loaded. Installed runtime, dashboard, schedules, recovery, and the combined release gates remain open.
