# Owner admission expired during concurrent source checks

Date: 2026-10-10. Question: Why does a concurrent native Algorithm read return `generating: false` without starting inference?

The combined daily text gate passes 455 tests and fails one native lifetime case. Three concurrent reads return HTTP 200 and `generating: false`. Owner admission completes, but no native owner child reaches the model. A separate direct owner command reaches inference with the same synthetic sources and model route.

The probe records actual subprocess output and elapsed time before changing code. Owner-job relay requests finish at 8.139, 8.149, and 8.145 seconds. Each returns the relay's generic HTTP 503 result. Source-view requests complete at 3.569, 6.914, 10.402, and roughly 13 seconds. The relay gives Algorithm reads 30 seconds but leaves job admission at eight seconds. Concurrent source-plan checks can exceed that shorter deadline.

The correction gives owner-job admission the existing 30-second allowance. The outer native asynchronous request still has its 40-second bound. The change preserves current authority checks and does not start a job after failed admission. The existing real HTTP lifetime test verifies one model request, a running child, and complete child termination after module stop.

Instrumentation remains in the [release evidence](../docs/verification/2026-10-10-daily-text-release/algorithm-probe-data.json). A first attempt modifies a disposable copy of the native tools and receives current-source refusal. The final probe observes subprocess output through the test listener without changing native program bytes. This distinction keeps the source guard active during the measured run.

The focused lifetime case passes after the correction. The final combined release repeat passes all 490 tests. The installed package also passes all 12 acceptance commands. No additional Hermes or LifeOS patch is required.
