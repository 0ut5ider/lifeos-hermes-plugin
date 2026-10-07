# Bind launch definitions separately from live process status

Date: 2026-10-05. The measurements use actual isolated user systemd services on Fedora 44.

The first barrier refuses a normal service because Fedora supplies `/usr/lib/systemd/user/service.d/10-timeout-abort.conf`. A rule that rejects all drop-ins cannot operate on this host. The service fingerprint now includes the physical unit and all supported drop-in file digests. The file reader permits trusted root-owned and current-owner definitions and refuses writable or changing sources.

The printed `ExecStart` property includes timestamps, the current process identifier, and exit status. Those values change during an intended stop or restart. They cannot identify a stable launch definition. A separate typed D-Bus query works while the service is active, but `GetUnit` returns "not loaded" after systemd unloads the stopped service. One `systemctl show` call still returns the static definition and inactive process state. The accepted barrier binds static properties and file digests, then checks main processes and control group emptiness separately.

Read-only `.212` inspection also confirms that `.claude` is an alias to `.hermes`. A direct-path-only PULSE working-directory check rejects that deployed layout. The transaction now captures the declared and physical installed roots, accepts the same physical working directory, and refuses a retargeted root before restarting services. The failing alias control and passing correction remain with the service evidence.

The final service and neighboring ownership gate passes 28 tests and 29 subtests. It verifies real parent and child process termination, both interruption phases, inactive-service preservation, changed-definition refusal, and changed-alias refusal. Application endpoint and owner-turn verification remain separate requirements. No production service or configuration changes.

Shared-memory MCP status still returns `integrity_error`. These measurements stay in the repository, with no alternate memory-record access.
