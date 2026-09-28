# Docker web cache path probe, 2026-09-28

The bridge classified cached web reads in local tests, and a synthetic remote test replaced the host cache prefix with a container prefix. I expected `to_agent_visible_cache_path()` to produce a path inside the active Docker backend.

On the isolated `.212` account, a disposable `composer:2.8` container saw the host cache at `/home/lifeos-hermes/.hermes/cache/web`. The first probe returned that same path as the agent-visible path. The host directory existed, but `ls -ld` at the path inside the container exited 2 with “No such file or directory.”

That first probe omitted Hermes's terminal policy scope. `to_agent_visible_cache_path()` reads `TERMINAL_ENV` from that scope, so it correctly behaved as a local call. Repeating the probe with `TERMINAL_ENV=docker` returned `/root/.hermes/cache/web/.`; `ls -ld` inside the container exited 0. The first failure was a test setup error, not evidence of a cache mounting defect.

A live regression then wrote a disposable file to the host `cache/web` directory. A real Docker `read_file_tool` read it through the mounted path, and the bridge sent its structured result to a `WebFetch` PostToolUse hook. The first assertion in this test expected a string response, but Hermes supplied an object with a `content` field. After checking that field, both live Docker file tests passed in 6.842 seconds. The cache file and containers were removed, and temporary Docker socket access was revoked.
