# Current native caller inventory

Date: 2026-10-05. This source-only pass refreshes the October 1 caller inventory against the freshly prepared interview-seed source. It reads installed public program files. It excludes USER, MEMORY, symlinks, dependencies, builds, and test trees. It does not read private records or deployed data.

The existing trace script scans 1,579 source files and records **236 candidates**, including 29 registered hooks, 149 declared entries, 50 imported callers, six configuration or documentation files, and two utilities without an active caller. The previous inventory has 227 candidates. The nine additions are the manifest loader, TELOS module, freshness cache, TELOS summary, interview scan, context freshness migration, TELOS freshness, state writer, and interview seed parent.

The copied scan script retains preceding source references as its discovery seed. The final inventory refreshes every available candidate's source hash and reference lines from this prepared source. `scan-comparison.json` records the added paths, source availability, and verified hashes. `source-traces.json` remains the preceding discovery seed. It is not the current source reference ledger.

Import edges and entry declarations identify callers to review. A governed API reference does not establish complete behavioral coverage. The source scan deliberately retains unresolved policy status. The prior static ledger remains incomplete even though later verification units cover selected surfaces. Complete caller coverage still blocks ownership activation.

The next review follows the current source paths and the existing effect evidence. Readonly numeric diagnostics, arbitrary-data repair tools, native file and prompt consumers, and scheduled authority need distinct policies. Source traces cannot replace actual permitted and refused effects.
