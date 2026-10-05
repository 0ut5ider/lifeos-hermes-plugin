# Fresh native installation path isolation

Date: 2026-10-05. The selected program and data homes stay separate from retained original data. No running `.212` profile changes.

The [native before control](native-before.json) calls actual ScaffoldUser and LinkUser tools with a separate program root and inherited current-home settings. Both tools exit zero. The new USER link resolves to the current data directory and exposes a synthetic retained marker. The plugin previously supplies the program root while retaining those source selectors.

The installer now binds child `HOME`, `CLAUDE_CONFIG_DIR`, `LIFEOS_DIR`, `LIFEOS_CONFIG_DIR`, and `PROJECTS_DIR` to the selected installation. It also supplies the explicit native configuration directory. The [failing path regression](tests-before.txt) reproduces the wrong link. The [corrected focused gate](tests-after.txt) passes 12 tests. The small payload uses actual settings, scaffold, link, and import tools with two instrumented deployment steps. It verifies names Adrian and Cerebo and exact preservation of the synthetic original store. It does not claim complete native deployment.

The [complete native installation](native-install-results.json) separately runs all six real installation steps from the pinned public source and all ten bundled patch groups. LifeOS 7.40.4 installs into a separate private fixture home. USER resolves to the selected data tree. Installed environment paths identify that home. The retained original tree has the same file hashes. Its marker is absent from the selected store. [The detached worker](run-native-install.py), [output](native-install-output.txt), and [exit marker](native-install.done) retain this result.

The initial small-payload run lacks the native atomic-write module and the neighboring Hermes test environment. [Its failures remain recorded](incomplete-fixture-tests.txt). The corrected fixture copies the actual dependency and the final command supplies the prepared Hermes source. Those initial errors do not count as a passing gate.

The complete native installer retains its shipped identity defaults. The selected Adrian/Cerebo identity still needs the reviewed fresh-store initialization path. Native deployment also leaves MEMORY inside the program tree, while governed ownership requires the external USER_DATA boundary. Complete memory setup, service and model acceptance, return, and release verification remain separate requirements. No ownership or service activation occurs.
