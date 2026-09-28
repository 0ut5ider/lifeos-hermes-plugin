# ConfigChange fingerprint regression

On 2026-09-28, the bridge compared watched files by modification time and size. A regression test rewrote `settings.json` with another valid JSON value of the same length, then restored its original modification time. The bridge emitted no ConfigChange event and kept the old active environment value. This was a demonstrated gap in detecting settings changes while a Hermes session was active.

The fingerprint now includes change time, device, and inode in addition to modification time and size. The same regression delivered `source: user_settings` to the hook and loaded the changed environment value. Existing ConfigChange audit and block tests stayed green. The full suite passed 104 tests on `.212` with no skips, and the installed bridge file matched the tested copy by SHA-256. The dashboard was restarted after installation.

This detects ordinary same-size rewrites with preserved modification time on Linux without reading every watched file each second. The watcher still polls once per second, so writes and reversions entirely between polls may be missed. Remote and container filesystems remain outside its watch set.
