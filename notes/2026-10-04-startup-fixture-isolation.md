# Startup fixture isolation

Date: 2026-10-04. The LoadContext handler writes its session timing marker to `/tmp/pai-session-start.txt`. The file on `.212` belongs to the active Hermes account. A synthetic HOME does not isolate this path. The paired startup fixture therefore mounts a private `/tmp` with Bubblewrap. The rest of the filesystem is read-only except the fixture home and the device mount. The fixture shares the network for its loopback HTTP guard.

The first source capture fails before execution because the standalone native reference has no `MemoryAccess.ts`. The managed Hermes source imports this dependency. The capture now records the dependency when it exists. The standalone control keeps its actual source. The first isolated Claude Code run then crashes before it emits any lifecycle event. Its bundled Bun 1.4.3 exits with status 134. This failure occurs even for `--version`.

Four probes compare the same Claude Code 2.1.272 binary. A read-only root fails with status 134, both with and without a private `/tmp`. Adding a device bind passes with status zero and prints `2.1.272 (Claude Code)`. Adding a separate `/proc` mount also passes. The fixture keeps the device bind and private `/tmp`. This isolates the timing file without preventing runtime startup. The probes identify the device mount boundary; they do not identify the specific device operation that causes Bun to abort.

The failed attempts remain under `/var/tmp/lifeos-paired-startup-20261004/` and the native account's `workspace/paired-startup-20261004/` on `.212`. Neither attempt establishes a passing hook effect. Candidate source, active services, and user data remain unchanged.
