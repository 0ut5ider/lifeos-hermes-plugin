# Trusted Docker project hooks

Date: 2026-09-28

After SSH project hooks worked, Docker remained a project registration gap. The isolated `.212` account could not reach the Docker socket, though the host had a working daemon and a cached `composer:2.8` image. A temporary socket access control entry let the test account create a disposable container. The entry was removed after verification.

The first live test wrote a synthetic `.claude/settings.json` inside the container. It rejected missing trust and a wrong image ID. The correctly trusted image ID still produced no hook decision, which confirmed the bridge selected only SSH backends. After the bridge bound trust to Docker's immutable image ID and a physical project root, the same test blocked the tool call.

The extended test changed project settings and a skill file. The watcher delivered `ConfigChange` with `project_settings` and `skills` sources. It then launched a remote asynchronous command, waited for the private result file, and observed its context on the next turn. A second test confirmed the async command still delivered context after its parent process exited. The runner reconnects with `docker exec` using the container ID it received when the hook started. If the container is removed before the runner executes, the hook fails and produces no context. A container-local HTTP server also returned a tool denial through the backend HTTP hook path.

Both live Docker tests passed together in 10.507 seconds on the isolated host. An initial probe and the direct project test left two running containers because Hermes's default `cleanup()` preserves containers across processes. The test now calls `cleanup(force_remove=True)` and waits for teardown. The two identified probe containers were removed. No other containers were changed.

A later trust-revocation probe edited a skill after the trust entry was removed. The watcher retained its project state, but `_run` rechecked the trust file before selecting hook groups. The project hook did not execute. The probe disproved a suspected authorization gap and remains as a regression test.
