# Remote ISA stale write reproduced on isolated SSH backend

On 2026-09-28, I created a disposable SSH account on `.212` and selected Hermes's SSH terminal backend in a temporary profile. A real `read_file_tool("ISA.md")` returned two lines from `/home/lifeosparityprobe/workspace/ISA.md`. A second SSH command changed the second line from `old` to `external edit`. A real `write_file_tool("ISA.md", ...)` then returned no `stale_write_blocked` flag or error and replaced the remote file with the stale `old` line plus `my edit`.

The native LifeOS ISAStaleWriteGuard reads `tool_input.file_path` with a local filesystem API. The SSH target path does not exist on the Hermes host, so its documented fail-open branch cannot protect this file. Hermes's own stale-write guard also calls local `os.path.getmtime` and `Path.exists` on the remote path. This probe confirms the combined behavior, not just the source-level risk. The remote account, key, and synthetic profile are temporary and contain no production data.

The next test must assert that an external change between a full remote read and a whole-file remote write causes a refusal, and that a fresh read permits a merged write. The fix must read state from the SSH backend that performs the write. The hook's native file-reading effect also needs a remote-aware route or an explicit statement that it cannot inspect remote files.
