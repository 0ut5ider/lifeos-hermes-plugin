# Fresh-store status listing

Date: 2026-10-05. The candidate adds `GET /memory/fresh/status` under the LifeOS plugin API. The installation owner reads every prepared fresh store for the current profile. Production on `.212` stays unchanged.

| Recorded state | Reported state | Reported content |
| --- | --- | --- |
| `review` with a valid signature for this profile | `review` | Names, active fact count, activation flag, source revision, and retained installation |
| `preparing`, and the installation lock is free | `interrupted` | Names |
| `preparing`, and an installation operation holds the lock | `preparing` | Names |
| Directory without a review document | `interrupted` or `preparing` | Identifier only |
| Altered review, another profile, or unreadable document | `invalid` | Identifier only |

The listing orders the latest preparation first. It reports `busy` when another installation operation holds the installation lock. The lock raises a distinct `InstallationBusy` error for that case. The listing refuses linked or unexpected entries in the private store directory and changes no file.

The route refuses query parameters with HTTP 400 and a missing session with the generic host HTTP 401. It refuses a revoked owner binding with HTTP 403. Successful responses and route errors carry `Cache-Control: no-store`.

The [nine new tests](tests-output.txt) fail before implementation ([before.txt](before.txt)). The final run passes 59 tests without skips. It includes the complete native preparation tests, the authenticated preparation route, both installation lock suites, and the neighboring memory routes.

The `busy` flag describes any installation operation, not only fresh-store preparation. An interrupted entry therefore reads as `preparing` while an unrelated update runs. This unit provides status only. A page control, detached restart-safe preparation, removal of interrupted stores, selected-store cutover, activation, and return acceptance remain open.
