# 2026-10-13: A version-only update changes its own reviewed timestamp

The real private browser update from 0.4.2-rc.1 at 307753c5 to the version-only b8895702 candidate refuses before publication. The release worker reports ProgramConflict. The active release and later synthetic user file stay intact.

Fingerprint comparison finds one changed source: generated/baseline.json. Its prepared created_at is 1791908692, and the worker-generated value is 1791908799. Every other baseline field, including all native file hashes, is identical. The worker reruns _program_plan before applying the prepared transaction. With native_changes false, that rerun creates a fresh timestamp. Earlier actual update trials change native programs and do not exercise this path.

The correction preserves the prior baseline creation time when native programs are unchanged. It still recomputes native file hashes and checks the installed tree against its baseline. The regression uses real Git, YAML configuration checking, native baseline and update planning, and ProgramTransaction. It fails before the correction and passes after it. A later native file edit still refuses. All 49 selected configuration, program, baseline, and update-plan controls pass.

Neither test candidate is published. Both must be rebuilt around the corrected worker before the public installation and numerical update trials.
