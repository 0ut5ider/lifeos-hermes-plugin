# Bind soul recovery to publication destinations

Date: 2026-10-04. The actual interruption control exits with status 73 after publishing `SOUL.md` and before publishing workspace context. Changing the configured workspace then allows the first candidate to restore previous context into a new directory. The [failing control](../docs/verification/2026-10-04-memory-hermes-soul-writer/recovery-destination-before-output.txt) reproduces this with synthetic files.

The journal stores exact destination paths. Recovery validates every recorded destination against the current configured profile and workspace before restoring any file. A changed destination refuses recovery and retains the journal. The caller must restore the original binding or use a reviewed aggregate recovery procedure. Aggregate service recovery remains open.

No production file or personal source changes. The original native soul template also states that Hermes cannot perform LifeOS work. Its role must be resolved during complete installation integration before production acceptance.

Two additional retirement controls fail after the initial expanded gate. A [direct service probe](../docs/verification/2026-10-04-memory-hermes-soul-writer/probe-retirement-output.txt) shows the name projection passing `None` as its timestamp. The history filter returns early when no retired records exist, so the initial controls miss the defect. Once a retired record exists, timestamp parsing raises `AttributeError` before claim comparison. The correction must supply the admitted source timestamp, including a valid empty-source fallback, and retain decoded-name filtering.

The [backup control](../docs/verification/2026-10-04-memory-hermes-soul-writer/backup-before-output.txt) shows the native snapshot accepting the unfinished external-output journal. Native capture now refuses that journal. Profile backup uses the same capture function. The control must then recover the actual pair and create a successful native snapshot.
