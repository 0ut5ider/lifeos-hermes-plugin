# Hermes learning graph built-in memory flags

Date: 2026-10-05. These controls run actual Hermes processes against isolated profiles. They use synthetic preserved memory files. They make no server changes.

The [baseline](before-output.txt) records nine failures, five passes, and two subtests. Disabled built-in stores still supply graph cards and detail text. Graph edits and deletions change both preserved files. The original [test source](baseline-test-source.py) and [process source](baseline-process-source.py) retain those controls. Enabled stores keep native behavior.

The graph now checks current per-store flags before it reads preserved memory. Detail and mutation operations refuse disabled sources. Mutation checks repeat during entry resolution under the native file lock. The [queued baseline](queued-before-output.txt) records four failures: a previously enabled store edits or deletes files after the selected flags change. The candidate rechecks current flags and preserves both files.

The [final bridge gate](final-output.txt) passes 20 tests and 33 subtests in 12.98 seconds. It includes graph controls, the LifeOS provider, patch regeneration, and patch packaging. The [native gate](final-native-output.txt) passes all 23 Hermes graph, mutation, and rendering tests in 4.34 seconds. Upstream unit tests retain their native fixtures; the added acceptance controls use real processes and actual files.

The [recorder](controls-output.txt) captures eight [passing controls](native-outcomes/). It retains exact before and after file content, selected flags, subprocess status, and output. The [source comparison](source-comparison.json) checks all assigned host files against the rebuild tree and all nine runtime patch copies. The [prepared manifest](prepared-source-manifest.json) identifies the exact distributed fixture. This change adds two files to the existing plugin-events patch group. It adds no dependency or patch group.

These results close the selected graph bypass. They do not establish aggregate cutover, stopped-profile writer draining, a configuration change barrier, malformed-configuration behavior, or every desktop route. Import, return workflows, Hermes management, jobs, voice, and the combined release remain open. Running ownership and sharing remain disabled.
