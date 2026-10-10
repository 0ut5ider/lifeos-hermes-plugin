# Pulse scheduler sleep exceeds the ownership drain deadline

Date: October 9, 2026, Toronto. The installed application check uses three separate acceptance units on .252.

The first ownership prepare drains the real Pulse process after approximately 41 seconds. Prepare completes and restarts the units. Apply immediately drains the next Pulse process. That process receives SIGTERM at 02:19:20 UTC. Systemd kills it at 02:20:05 UTC, after its 45-second stop deadline. ProfileServices also has a 45-second command timeout. Ownership remains disabled because the drain fails before configuration publication.

Native Pulse records the signal but waits in Bun.sleep before cleanup. Its scheduler caps that sleep at 60 seconds. The regression test starts the actual daemon with no jobs and sends SIGTERM during idle sleep. Both Observability configurations fail the three-second exit assertion. The initial fixture attempt cannot resolve smol-toml. The corrected fixture uses the existing verified native dependency trees. The dependency failure is separate from the reproduced shutdown failure.

The patch replaces only the scheduler sleep with a cancellable timer. SIGTERM or SIGINT resolves that wait. Existing cleanup still stops on-demand child jobs and writes final daemon state. The native test passes both configurations in 0.768 seconds total. The local patch-bundle and shutdown controls also pass. Four installed cases pass in 26.287 seconds, including real held inference children for Conduit, Atlas, and Algorithm summaries. These child cases use the retained synthetic HTTP inference fixture, not the private model server.

The isolated operation returns through actual OwnershipSetup.recover. Ownership stays disabled. The next backup and activation complete. Its application read fails because the operator omits the pulse_http dashboard relay setting. The operator also names a nonexistent TELOS summary endpoint and records an incorrect source-directory level during recovery. These setup errors receive separate correction and retained evidence. They do not justify weakening authenticated admission or the service timeout.

No live bot credential, live profile, or live service definition changes. Acceptance units use separate ports and remain disabled for boot. Main Pulse is the selected dashboard. Separate Telos deployment remains outside this release.
