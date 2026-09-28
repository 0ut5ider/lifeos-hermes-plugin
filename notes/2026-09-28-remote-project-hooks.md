# Trusted SSH project hooks

Date: 2026-09-28

The bridge previously ran only local project registrations. A remote tool's `cwd` stayed in the hook payload, but the bridge could not load or execute the SSH project's `.claude` settings. A host path with the same spelling was deliberately excluded.

## Transport probe

Hermes's SSH environment accepted `stdin_data` for an executed command. A disposable account on the isolated `.212` host received a 200,013 byte input with an identical SHA-256 digest. The SSH environment merged stdout and stderr, so the new transport frames a remote command's exit code and both streams as base64. A live test passed a 200,000 character prompt to a remote command and recovered its JSON stdout and separate stderr.

## Trust and behavior

The bridge reads a local owner-controlled JSON trust file. Each entry binds a physical remote project root to the active SSH backend's host, user, and port. A remote `pwd -P` check rejects a working directory outside that root, including a symlink escape. The bridge loads the remote project's settings and runs its command hooks in the remote working directory. HTTP hooks address only loopback on the remote backend. Asynchronous hooks save their input in a private spool, reconnect after the parent exits, and deliver context on the next turn.

The `ConfigChange` watcher polls remote settings and skill digests once a second while a session uses the project. The test changed `settings.json`, `settings.local.json`, and a remote skill file. The corresponding hooks observed those changes. A first red test for skill edits had no watcher path; after adding the scan, the live test passed.

## Verification

- Five live SSH tests passed together on `.212` in 11.030 seconds after the final `curl --noproxy` and shell `builtin pwd` hardening changes. They cover transport, trust and symlink escape, asynchronous survival, remote loopback HTTP, and ConfigChange.
- The full local suite passed 151 tests with 43 optional skips. The full `.212` suite passed 151 tests with 38 optional skips. Both runs used the hardened code.

The disposable account and key were removed after verification. The account had active SSH sessions, so `loginctl terminate-user` was required before `userdel -r` succeeded. Container projects still need a separate backend implementation.
