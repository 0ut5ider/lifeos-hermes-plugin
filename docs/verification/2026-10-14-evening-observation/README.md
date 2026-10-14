# Owner-rescheduled automatic acceptance

On October 14, Adrian requests moving the Thursday morning acceptance to Wednesday evening, about ten minutes after the request. The actual Pulse job is due at 18:02 Toronto. Its existing command, owner admission, private model mapping, output, and Cerebo destination stay fixed. Only the selected user cron expression changes from `0 7 * * *` to `2 18 14 10 *`. The expression is specific to October 14. No manual job or substitute message supplies acceptance evidence.

The installed format 2 observer requires 07:00. The isolated operator therefore uses an explicit format 3 rescheduled window from 18:02 through 18:17. It uses the installed qualified execution and Discord validators. It checks the exact active package, selected configuration hash, active Pulse timezone, single cron start and completion, current job state, complete Discord window, and exact single delivery during execution. The receipt states `original_0700_wall_clock_observed: false`. This scope must remain explicit in release evidence.

The configuration transformation passes two tests with invalid, duplicate, disabled, changed, and round-trip definitions. A read-only probe against the actual installed cron matcher passes four cases: no early run, due at 18:02, no duplicate after restoration, and the normal 07:00 job due tomorrow. The probe executes no job. The actual native config loader selects the evening script definition after Pulse restarts. Gateway and dashboard stay active.

The transient user timer `lifeos-evening-observer-20261014.timer` runs at 18:17. It observes without sending a message and restores the normal schedule afterward, including on observer failure. The fallback `lifeos-evening-restore-20261014.timer` runs at 18:19. Its restore action restarts Pulse even if a prior interrupted restoration already changed the file. The app follow-up runs in this thread at 18:18. It reads the safe receipt, verifies restoration, and removes its app schedule after the first observation. It can cancel the fallback timer after a verified successful restoration.

The operator is `/home/lifeos-hermes/releases/observe_rescheduled_20261014.py` on `.253`. Its private request and original configuration stay under `/home/lifeos-hermes/.hermes/operations/evening-acceptance-20261014`. Export only the safe observer receipt. Do not export the original configuration, narration, credentials, or personal records. The complete package and all published assets stay unchanged.

The app schedule title and identifier are in PREPARATION.json. To cancel before execution, first use the operator restore action as lifeos-hermes with its existing venv and user systemd environment. Then stop the two owned timers and remove the app schedule with `delete_scheduled_task`. Do not start the job as a cancellation or verification step.

## Recorded outcome

The installed observer returns FAIL because the Pulse state time precedes journald capture by 0.475 milliseconds. The original receipt remains in initial-observer-failure.json. Pulse records one successful automatic start at 18:02:53.006 and completion at 18:03:19.076. The native completion event timestamp agrees with the millisecond state exactly. The later journal capture timestamp is not the native completion clock.

The staged fix uses the native event timestamp for state correlation and separately bounds journal capture delay to five seconds. A regression with the measured delay fails before the fix. All 12 observer tests pass afterward. The test set also rejects invalid timestamps, stale state, duplicate execution, incomplete Discord coverage, and multiple deliveries.

The isolated read-only replay uses that staged validator on the original recorded cron events. It uses the unchanged installed Discord checker to cover the entire 18:02 to 18:17 window. The checker scans 58 messages and identifies exactly one Cerebo delivery, message 1560050392140742737, at 18:03:17.821. The corrected receipt is automatic-rescheduled-verification.json. It preserves the original failure and binds the isolated validator hash. It does not claim that the installed observer passed. No job, generation, or send runs again.

The regular 07:00 schedule and all original configuration bytes are restored. Pulse, gateway, and dashboard are active. The app schedule is deleted and both owned timers are inactive and collected. The installed 0.4.3 package stays unchanged. The timestamp fix is staged for the next complete qualified release.

The owner-rescheduled automatic-delivery check passes, subject to focused review of the correction and evidence. The 07:00 wall-clock observation remains unperformed. The new safe asset must preserve this scope and all existing release assets.
