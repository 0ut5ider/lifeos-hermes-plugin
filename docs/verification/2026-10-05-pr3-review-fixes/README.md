# Review corrections for pull request 3

Date: 2026-10-05. An [independent runtime review](../../agents/2026-10-05-pr3-runtime-review/pr3-runtime-review.md) reads the runtime package and host patches at commit `71987ce`. This unit corrects two findings that the primary agent confirms in the code. Production on `.212` stays unchanged.

| Finding | Confirmation | Correction |
| --- | --- | --- |
| Required memory checks fail open on an unsupported host version. | With lasting memory enabled and a middleware interface version other than 1, registration added no check and raised no error. | Registration now raises `MemoryAdmissionError` in that case. A disabled runtime still loads. |
| Fresh-store preparation holds the configuration lock during the native installation. | A second descriptor could not take the lock while the installer ran. Revocation and the sharing switch need that lock. | Preparation now holds only the installation lock. Each owner check takes the configuration lock for the read. |

The four new tests fail before the correction ([before.txt](before.txt)). The final gate passes 204 tests with one optional skip ([after.txt](after.txt)). It includes the complete native preparation tests and the provider suite.

## Findings that remain open

The primary agent confirms the first finding below against the real fixture. The other findings are recorded from the review and are not yet corrected.

1. Profile backup has no exclusions and a 256 MiB limit. The active `.212` profile directory measures 8.6 GB, so a profile backup and ownership preparation cannot complete there. The backup scope needs a design decision.
2. Ownership recovery stops services before a rollback that can fail. No caller exists yet.
3. The Bun wrapper applies the frozen-lock check only to the exact `bun install` form.
4. The fresh-store status probe takes the installation lock for a moment, so a concurrent operation can receive a refusal.
5. Failed fresh stores stay on disk without a limit or a removal action.
6. State paths for named Hermes profiles resolve inside the Hermes root.
7. The backup command reports one generic message for every failure.

The review did not read `memory_native.ts`, the `lifeos-memory-access.patch` content, or about 25 further memory modules. Its report lists them.
