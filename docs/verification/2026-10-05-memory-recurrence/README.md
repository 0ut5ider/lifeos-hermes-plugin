# Governed native recurrence ledger

Date: 2026-10-05. Role: primary implementation and verification.

Managed native recurrence reports, events, clusters, and patch history consume current admitted source snapshots. Collection covers verification, format, writing, tool-failure, and hook-healer streams, plus native failure captures and the patch registry. It checks unrestricted owner recall, the installed root, fixed physical paths, decoded private fields, retirement, source bytes, and current authority. Missing context, redirected sources, and revoked accounts refuse delivery.

Patch registry publication also requires unrestricted owner write access. The service validates the native record fields and current policy before checking a saved receipt. Native JSON serialization retains the tested bytes. The operation journal publishes mode 0600 files, preserves later edits on conflict, and recovers previous bytes after process death. A stable request identifier returns the same receipt without another append.

## Evidence

The baseline records 12 failures, two passes, and four passing subtests in 1.78 seconds. The failures cover owner policy, private and retired rows, redirected sources, unauthorized writes, and file permissions. Four authorized library comparisons match original-native report, event, cluster, and registry results. The first candidate passes ten tests and eight subtests in 5.83 seconds.

Expanded controls reproduce three candidate defects. Capture timestamps differ from native ISO formatting. Discovery limits apply separately to each directory instead of the complete capture discovery. A retry conflicts with its own saved receipt because its payload includes the previous registry digest. The final candidate formats timestamps through the native Date object, counts discovery entries across directories, and uses the stable request inputs for receipt identity. Destination snapshots still protect publication.

The combined final gate passes 69 tests and 35 subtests in 53.83 seconds. The stream and capture controls compare original-native results across three library functions. Actual interleavings change a source, registry destination, or account after a real native operation. They refuse delivery or publication and preserve the expected bytes. An actual exit with status 73 after publication leaves changed registry bytes. A subsequent transaction restores the previous registry.

The recorder retains 18 passing controls with actual process output and synthetic registry bytes. All 54 compared native files match the distributed prepared tree. Root/runtime patch pairs match. The final command records source hashes. No dependency or patch group is added.

## Limits

These controls use synthetic data and actual Bun library calls. They do not prove live scheduling, model judgment, hypothesis derivation, healing fixture publication, restricted prompts, complete source coverage, aggregate ownership recovery, or activation. The source limit remains 256 KiB. Discovery and row limits are 2,048, and the corpus limit is 3 MiB. Unsupported native row shapes fail closed. Registry writes refuse excluded current registry content rather than rewrite that content.

The public native tools package has no typecheck, lint, test, or build script. Bun executes the exercised paths; this gate does not establish a complete TypeScript typecheck. No production server, configuration, ownership, or sharing setting changes. The combined release gate remains open.
