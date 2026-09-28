# SSH web-cache safety route

Date: 2026-09-28. The bridge already classified reads from Hermes's browser and web cache as `WebFetch` for local and Docker backends. SSH remained untested because Hermes renders synced cache files under `~/.hermes` on that backend.

The isolated `.212` account connected its real Hermes `SSHEnvironment` to a disposable loopback workspace. A temporary cache file contained `SSH_CACHE_CONTENT`. Hermes translated its host path to `~/.hermes/cache/web/...`, `read_file_tool` returned the content through SSH, and the bridge's `PostToolUse` callback invoked a `WebFetch` matcher with the same content. The test passed in 1.364 seconds against installed Hermes commit `48f0a3d12d5`.

The test used `probe_only=True` because a full SSH environment synchronizes the complete Hermes home before execution. An initial probe was stopped during that unnecessary sync. The disposable SSH key, authorized-key entry, workspace, and cache file were removed. This proves the loopback SSH read and matching route. It does not test a distinct remote host, which would additionally depend on Hermes cache synchronization.
