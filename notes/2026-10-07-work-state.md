# Work identity and cleanup races

Date: 2026-10-07. Eight actual native learning processes write one record when different sessions share a title and minute. The native filename provides the collision: capture date, minute, and title. A hash of session and work slug retains eight records. The recorded work origin also preserves identity across capture days. An ISA without a creation date needs the registry start fallback; otherwise a next-day repeat writes a second file.

After the filename correction, a 100 millisecond delay before the native session-name write exposes a second race. Overlapping cleanup processes restore six names that other processes removed. One earlier forced overlap also leaves a work row active. Both programs mutate shared lifecycle files across session identities.

The bridge's existing operating system advisory lock now covers the installed learning and cleanup programs with one shared lifecycle scope. Detached requests carry that scope to the real runner. The synchronous and detached eight-session controls retain eight records, complete all eight rows, and leave no names. The detached control observes sixteen actual process exits after the parent closes. Repeated finalization retains one learning record. This result concerns lifecycle coordination; interrupted learning publication still needs its own measurement.
