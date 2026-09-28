# Invalid managed file policy

Date: 2026-09-28. An independent Astra review found that malformed managed permission settings produced an `unknown` file decision. Bash requested review for that decision, but local direct Read and Write could continue. A native PermissionRequest grant could therefore approve a direct Write despite the invalid managed policy. The review fixture reproduced the inconsistency; native Claude Code behavior with malformed managed policy was not measured.

The bridge now distinguishes an invalid policy from an ordinary unresolved path. An invalid policy requests review for Bash and direct file tools, including a direct Write granted by a native PermissionRequest hook. An outside-workspace path still returns `unknown` and follows its existing policy. A regression covers malformed JSON in `managed-settings.json`, a real permission-hook child process, and direct Read and Write calls. A unit test covers malformed rule syntax separately.

The local source suite passed 281 tests with 66 optional skips. The isolated `.212` source suite passed 281 tests with 55 optional skips. Both emitted existing warnings because some optional remote settings imports were unavailable. This change has no live malformed-policy probe on the installed gateway; the installed bridge was checked by its plugin doctor after deployment.
