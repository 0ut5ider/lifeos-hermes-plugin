# Dashboard response authority

Date: 2026-10-08. This check covers the authenticated dashboard preference path with synthetic data and real native readers.

The [baseline](baseline.txt) fails all three targeted cases. Wiki, Knowledge, and Pulse snapshots return after the operator removes the authenticated owner binding during actual native rendering. Earlier native service response tests do not cover these preference methods.

The preference methods now validate the current owner configuration before they return an installation-bound response. The same final check covers hypothesis reads, freshness, and graph responses. Existing freshness, graph, and hypothesis callbacks remain in place. Unchanged requests retain their existing response contents and installation binding.

The [focused gate](authority-gate.txt) passes the three reproduced cases. The [expanded adjacent gate](adjacent-gate.txt) passes 67 tests without skips. It includes actual authenticated HTTP routes for Pulse, wiki, Knowledge, and hypotheses. Five targeted tests cover revocation after actual rendering, a changed configuration with the owner binding retained, and unchanged responses. The native observer returns the real renderer output before it changes the selected configuration. It does not provide a fake result.

The [source receipt](source-identity.json) records the edited preference source and test hashes. This change governs final preference responses. It does not claim that every raw native file reader rechecks source bytes after rendering, or that installed application acceptance is complete. The release remains staged and fresh-store ownership remains disabled.
