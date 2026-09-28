# Native ISA stale write guard in Docker

Date: 2026-09-28

The hook parity record previously had only simulated Docker paths. A live disposable container on the isolated `.212` host supplied an `ISA.md` file absent from the Hermes host. Hermes `read_file_tool` returned the file, and the bridge sent the backend digest to the installed LifeOS `ISAStaleWriteGuard` PostToolUse hook.

An external container edit changed the file after that read. The installed `PreToolGuard` blocked the proposed whole-file Write with the native stale-write message. A second Hermes read refreshed the view, and the same hook no longer blocked a Write with current content. The one live test passed in 3.001 seconds.

The test used a temporary Docker socket access entry for the isolated Hermes account. It called forced container cleanup, waited for teardown, and removed the socket entry. It did not execute a file Write after the native allow decision. Other container file operations still need coverage.
