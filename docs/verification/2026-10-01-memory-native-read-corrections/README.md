# Native source read review corrections

Date: 2026-10-01. Work uses disposable synthetic profiles and pinned prepared public sources. No running installation changes.

## Confirmed findings

The [Astra review](../../agents/2026-10-01-memory-native-read-review/memory-native-read-review.md) passes the existing 107 tests and then reproduces two missing behaviors. The primary agent independently reruns its probes. The raw result is [root-probes-before.json](root-probes-before.json).

1. A safe source body with a private-marked filename publishes its filename in native titles, slugs, groups, and paths. Body validation alone does not validate source metadata.
2. Directory enumeration consumes all entries before refusal. Hidden entries and non-source WORK entries bypass the count. Per-root counters also fail to bound the complete discovery operation.

The primary adds five regression tests. All five fail against the preceding implementation. [before.txt](before.txt) records the failures. After correction, all 23 corpus tests pass in 10.928 seconds. [after.txt](after.txt) records this result.

## Corrections

The source collector submits each complete source path with its body to the existing native private-content and control-character validator. Rejected sources remain unchanged on disk. The renderer receives no rejected source metadata.

The collector uses streaming `os.scandir()` and checks the count before filtering or sorting. Hidden entries, directories, and non-source files consume the same budget. All retained silos share 2,048 discovery entries. The collector refuses on entry 2,049. The separate selected-source cap remains enforced. Excess discovery refuses the whole view instead of publishing a partial index.

Python 3.14 `Path.iterdir()` materializes its directory entries before it yields them. Moving a counter inside that iterator would not bound allocation. The real iterator instrumentation in the regression tests observes the underlying filesystem scan.

## Verification

The primary [expanded gate](gate.txt) passes 124 tests in 121.219 seconds, without skips, failures, or errors. This repeats all eight modules from the first review and adds the five regressions plus 12 Hermes provider, source preparation, and patch tests. [gate.done](gate.done) contains exit status 0. [run_gate.py](run_gate.py) preserves the command, prepared source path, preceding commit, and exact working diff.

The [public documentation probe](documentation-probe.json) still admits 58 of 60 pages from the 1,443,524-byte corpus. Three collections take 0.426, 0.418, and 0.366 seconds. The two native private-boundary examples remain excluded. This correction does not change source classification or retirement-clock policy.

The correction changes two plugin modules and their corpus tests. Distributed native patches remain unchanged. Their two copies remain identical. The bundle still contains nine Hermes and ten LifeOS patch groups. The prepared source remains `source-gate-20261001-knowledge-relay-final`.

The [fresh Astra closure](../../agents/2026-10-01-memory-native-read-closure/memory-native-read-closure.md) independently passes 66 tests in 47.903 seconds and ten isolated probe cases. It closes both findings and confirms no additional material defect in the reviewed paths. The primary gate includes all 66 test cases, and the primary separately reruns all ten final probes. [root-closure-probes.txt](root-closure-probes.txt) and [raw/closure-probes.json](raw/closure-probes.json) preserve that rerun. Source hashes match the independent snapshot.

Product code, tests, and written documentation pass the Git whitespace check. Adding raw diff artifacts produces whitespace warnings on their single-space context lines, including the diff embedded in `gate.txt`. These are required unified-diff prefixes. The artifacts retain their exact captured bytes; no whitespace rule or hook is disabled.

## Limits

The discovery limit now includes entries that do not become wiki pages. A large hidden or unrelated population can therefore make the wiki unavailable. This refusal is deliberate and bounded. It does not establish whole-operation latency under contention or an atomic snapshot against outside filesystem writers.

This bounded read correction does not close verified code-source classification, reviewed whole-note editing, actual mount and sidecar publication, derived readers, restricted delivery, lifecycle, recoverable ownership, or the complete release gate. Memory ownership remains disabled on running installations. No server deployment, push, or shared-memory import occurs.
