# Interview SeedPulse child controls

Date: 2026-10-04. These controls run the shipped interview SeedPulse command and its actual generator children. They use synthetic identity and TELOS sources. They make no server changes.

The [candidate gate](candidate-output.txt) passes 49 tests and 15 subtests in 24.98 seconds. It includes all seven parent controls and both generator suites. The [native recorder](controls-output.txt) retains seven [command outcomes](native-outcomes/), artifact bytes, and permissions. The [source hashes](native-source-hashes.json) identify the tested native command and generators.

The admitted parent runs GenerateTelosSummary.ts and UpdateLifeosState.ts. Both artifacts have mode 0600. Native health scoring reports 50 percent. A dry run reports available generators without writing. Missing context and restricted authority refuse both children. Revocation preserves both previous artifacts. An explicit installed alias retains the governed root. An empty runtime reports both missing generators and refuses publication.

The existing child protections satisfy these selected parent cases. This unit makes no product-code or patch changes. SeedPulse does not create PULSE manifests. These controls do not establish a transaction across both independent generators, interruption recovery for the complete interview, aggregate ownership activation, or a live server setup. Those release gates remain open.
