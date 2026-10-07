# Cold system publication needs an optional registry check

Date: 2026-10-04. Six initial deny-hash controls pass. The permissions control invokes publication first and fails. The owner control first runs a dry review, then publishes successfully. Five direct cold attempts all refuse before an operation receipt exists.

The [fixed-target probe](../docs/verification/2026-10-04-memory-deny-hashes/probe-cold-target-output.txt) identifies `samefile` comparing the existing environment file with a registry that does not exist. The comparison raises `FileNotFoundError`. The dry run creates the registry and therefore hides the defect. The shared publication resolver now checks whether the registry exists before comparing aliases. It retains the comparison whenever a registry exists.

All environments and sources are synthetic. This result concerns the candidate hash writer. No production file changes. The shared resolver also serves fixed system writers, so regression coverage must include system publication and existing registry-alias refusals.

The [environment control](../docs/verification/2026-10-04-memory-deny-hashes/environment-before-output.txt) then exposes CRLF conversion during salt publication. The [boundary probe](../docs/verification/2026-10-04-memory-deny-hashes/probe-environment-output.txt) measures two CRLF sequences in the file and zero in the admitted text. The environment reader now preserves line endings through the existing bounded source collector. Other source readers retain their current newline behavior.
