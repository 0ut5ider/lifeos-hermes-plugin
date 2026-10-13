# 2026-10-12: Native preparation blocks a passing release suite

The exact stable archive passes all 625 integration checks in 979.5 seconds.
A stock fresh installation also passes recovery from an actual exit 73 at directory-retained.
The development update passes recovery from actual exit 73 at programs-published.
Two later unchanged development preparations fail at native Observability dependencies.
Bun 1.3.14 reports a Next.js tarball-extraction failure.
The release remains unpublished.

The guest has 43 GiB free and 88,584,368 free inodes at the first investigation checkpoint.
The successful and failed Next.js 15.5.27 caches each contain 7,278 files.
Their complete content maps have the same SHA-256, `b181f85b41c0856a9ea2a328a25bd0eba958589288e3c47e4e3a6bcdfeebc482`.
This evidence rejects incomplete retained payloads as the explanation.
It does not prove that every network response arrived intact.

A replay of the public DeployCore command in the retained failed installation passes.
A fresh public installation under filesystem syscall tracing also passes.
Both traced runs have a 1,024-file soft limit and a 524,288-file hard limit.
The traces show no descriptor-limit or storage-exhaustion error.
The passing traced runs do not exclude a timing-dependent extraction failure.

[Bun issue 34821](https://github.com/oven-sh/bun/issues/34821) records related streaming extraction failures.
The maintainer fixes include first-chunk handling and later truncated-response handling.
The official Bun 1.4.3 release contains the later fix commit: the compare result has zero commits behind.
This is an attribution hypothesis until the isolated runtime comparison finishes.
The comparison changes only the tested runtime version and keeps every native dependency lock unchanged.
All comparison installations use separate synthetic homes.
No experiment changes the active profile or either release asset set.

The untraced comparison now finishes.
Bun 1.3.14 fails one of two new cold installations; the second passes.
Bun 1.4.3 passes all three new cold installations.
The independent post-install verifier checks all twelve frozen locks in each of the five installations.
Every lock hash matches the original catalog.
The actor preserves the active release receipt across every case.
These results support replacing the extraction-failing runtime with the fixed upstream runtime.
They do not guarantee that every future registry request will succeed.
The stable package must be rebuilt and its qualification repeated before publication.
