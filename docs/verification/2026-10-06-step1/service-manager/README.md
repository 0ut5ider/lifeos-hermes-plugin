# Source-bound service admission repeat

Date: 2026-10-06. All 26 selected service, ownership setup, and restarted-host tests pass on development container `192.168.8.252`. The tests use the actual user manager for the disposable UID 1007 account. They preserve stable active or inactive admission, actual service writers and children, definition checks, durable stop intent, recovery, and original inactive service selection.

The workstation regression run records one service-state error. A 20-case instrumented repeat reproduces one refusal. The raw systemd journal reports failed inotify watch creation and a stopped Pulse service timeout. A process-level count finds 138,625 watches against a limit of 138,629, with 138,522 held by Zed. `refusals.jsonl` and `watch-count.json` retain those observations. No product policy or workstation kernel setting changes.

The development repeat has its own user manager and a watch limit of 4,194,304. Initial broader repeats lack native memory source, Hermes source, or dependency generation bindings. Those runs remain failed. The final command binds the prepared native source and the actual managed Python generation. The launcher starts `user@1007.service` without enabling lingering. Final cleanup stops that test manager after the remaining verification.

The restarted-host test uses a synthetic local HTTP model response to verify memory provider transport. It supplies no real inference evidence. The separate paired CLI controls retain real private FlashNext evidence. The service repeat resolves the measured service-state failure in a resource-sufficient manager; it does not turn the earlier full regression result into a clean pass.
