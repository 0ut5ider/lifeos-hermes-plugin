# PULSE destination conflicts

Date: 2026-10-04. The probe uses the real service, native schema, publication journal, and file system. It inserts actual destination bytes between collection and publication. It replaces no native result.

The [baseline](before-output.txt) has two failures and eight existing data-plane passes. Both a later log append and a later page edit are erased, while the operation reports success. The publication helper captures destination bytes after collection, so it treats the later edit as its comparison baseline.

The service now captures destination bytes during initial collection. The journaled operation compares the current destination with those earlier bytes before writing. A changed log, page, metadata, error, or index causes refusal. The later bytes remain intact. Page/metadata interruption recovery remains covered by the preceding adapter controls.

The [focused correction](candidate-output.txt) passes 35 tests and 10 subtests. The [final gate](final-output.txt) passes 136 tests and 92 subtests in 117.20 seconds. Pytest collects eight existing data-plane tests imported by the new test module in addition to the explicit final test list. All recorded [source hashes](final-command.json) match. The native distribution and both patches remain unchanged. No server changes occur.

Model generation and complete adapter output transactions remain separate requirements. This correction does not activate memory ownership or sharing.
