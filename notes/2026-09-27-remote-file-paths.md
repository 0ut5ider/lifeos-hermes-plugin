# File hook paths in remote task namespaces

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

Hermes resolves a relative file path against the task's backend namespace. The bridge previously joined the path to the local account's working directory before asking Hermes to resolve it. With an SSH task anchor of `/remote/work`, the installed bridge produced `/home/lifeos-hermes/work/notes/test.md`; Hermes's own resolver produced `/remote/work/notes/test.md`. That mismatch could route a LifeOS file hook to the wrong path.

A regression test first confirmed that the bridge passed the local absolute path to a task resolver. The bridge now passes the original relative path to Hermes's resolver. On `.212`, both the bridge and Hermes returned `/remote/work/notes/test.md` for the SSH namespace probe. With a simulated Docker task root of `/workspace`, both returned `/workspace/notes/test.md`. The local suite passed 85 tests with six optional native skips.

The probes used Hermes's real path resolver with backend identity and roots supplied by the test. They did not connect to a remote SSH host or start a container. Live backend file operations still need separate end-to-end verification.
