# Overview candidate caller inventory

Date: 2026-10-08. This scan uses the fixed prepared TELOS overview candidate.

The existing scanner reads public program sources and verifies every recorded source hash against the prepared tree. It uses the preceding manual entry-point declarations and historical seed to discover current candidates. It does not read USER or MEMORY records, dependency files, or symlink targets.

The scan refreshes source lines, call edges, and file hashes after index publication, TELOS editing, frontend type correction, and overview changes. changed-programs.json records every difference from the business-view inventory. source-identity.json records the selected root and the hash check result.

An API reference is not behavioral acceptance. The inventory retains unresolved classifications. Operational dashboard readers and live stream delivery still require their own tests. This scan does not establish complete caller coverage or permit memory activation.

The first refresh counts 331 candidates because an unmanaged native comparison creates a synthetic user-index cache in LIFEOS/PULSE/state. The scanner now excludes that runtime directory before it opens any file. The baseline cache-exclusion test fails with a UTF-8 decoding error on deliberately invalid cache bytes. All four inventory tests pass after the correction. The corrected scan verifies 330 candidates in 1,579 public files. Earlier outputs remain under before-cache-exclusion filenames.
