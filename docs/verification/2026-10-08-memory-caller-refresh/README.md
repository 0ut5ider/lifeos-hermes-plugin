# Native caller refresh

Date: 2026-10-08. This scan uses the prepared Knowledge command candidate. It reads public installed program files and excludes USER, MEMORY, dependencies, symlinks, build output, and test trees. It does not read deployed personal records.

The [scan](scan-output.json) records 1,579 source files and 236 candidates. The candidate count matches October 5. The inventory includes 29 registered hooks, 149 declared entries, 50 imported callers, six data files, and two exported utilities without an active caller.

The [source identity receipt](source-identity.json) verifies all 236 current source hashes. It finds no missing source. The current `caller-inventory.json` replaces preceding reference lines with lines from the selected candidate. `source-traces.json` remains the preceding discovery seed.

There are 58 direct governed API references and 178 candidates that require boundary classification. A reference does not establish effect coverage. Imported callers can receive authority through their entry point. Public metadata, runtime work state, administrative utilities, optional integrations, and lasting-memory sources require separate classifications.

The fresh daily release excludes the selected optional integrations and defers import workflows. This scan does not classify every remaining candidate as safe and does not establish complete caller coverage. The remaining review must connect each selected source or publication boundary to permitted and refused effects before ownership activation.
