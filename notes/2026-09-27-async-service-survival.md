# Async hook survival under systemd

Date: 2026-09-27

Hypothesis: `start_new_session=True` keeps an async hook alive after a one-shot Hermes process exits, but does not move it out of the parent systemd service control group. A service restart or stop can therefore kill the hook.

On the isolated `.212` account, a transient parent user service started a child with `setsid` and exited. After three seconds, the child's marker was absent. A control probe started the delayed child in its own transient user service; its marker existed after three seconds.

The bridge now starts async hook runners with `systemd-run --user --collect --service-type=exec` when available. The hook command, JSON input, working directory, and environment stay in a private `0600` spool file. The runner removes that file before invoking the hook. If the user service cannot be started, the bridge uses its prior detached subprocess path. A regression test first showed that an isolated runner did not restore the environment or working directory from its spool file. It passed after the runner change.

An end-to-end `.212` probe launched the bridge inside a disposable user service. The parent exited after roughly three seconds; its async hook completed later in a different user service and wrote its marker. The first version of that probe removed its temporary directory four seconds after launch, before the two-second hook had completed, and therefore reported failure. An eight-second wait showed the hook completing. No production service was changed. The full local suite passed 80 tests with five optional native tests skipped.

The fallback detached process remains vulnerable to service managers that kill the parent's control group. Other service managers have not been tested.
