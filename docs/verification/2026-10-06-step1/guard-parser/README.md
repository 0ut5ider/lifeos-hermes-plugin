# Native guard parser checks

Date: 2026-10-06. These controls use installed native hooks and the actual bridge.

The shell write matrix covers seven forms, two content classes, and three target zones. All 42 checks pass after the parser correction. Allowed commands execute against disposable files. Blocked commands retain the prior file content. Additional controls cover clean public destinations, cached private and internal destinations, confirmed-public denial, malformed inputs, and guard failure isolation.

The [before control](escaped-literal-before.json) records a real gap. The native guard returns exit 0 for a Python command whose literal path uses shell quote concatenation. The actual shell then writes `PAIR_DENY_TOKEN` into the protected target. The patch decodes that literal quote sequence for target discovery. The deny scan keeps the original command. [guard-parser-after.txt](guard-parser-after.txt) records five passing tests, including the full matrix.

The correction does not inspect variable values or copied file contents. An explicit control retains the native limit for a copy command that reads restricted content from a separate file. Shell policy still needs independent permission controls.

Six [RTK controls](rtk-tests-complete.txt) use the actual official `rtk 0.51.0` executable. They check field preservation, Git flags, environment prefixes, shell chains, GitHub CLI metadata help, unchanged read commands, and a later native deny after a rewrite. [rtk-source.json](rtk-source.json) binds the verified release download. These are direct native hook and bridge controls, and do not claim native CLI dispatch.

The [source gate](source-tests-complete.txt) passes 16 preparation and installation tests. It applies the added patch through both ordered preparation and the distributed installer list. The first gate uses `/tmp` and fails its clone on the bounded temporary filesystem. The corrected gate uses a short disk-backed fixture root and the prepared Hermes import path.
