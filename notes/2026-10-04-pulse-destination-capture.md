# PULSE destination capture

2026-10-04. Native adapter publication passed its source and authority checks. A separate scheduling probe found a destination race.

The probe writes real later bytes after collection and immediately before the publication helper. Both the log append and page replacement report success and erase those bytes. The baseline has two failures and eight existing data-plane passes. Capturing destination bytes inside the publication helper is too late: the helper accepts the later edit as its baseline while still publishing output prepared from earlier state.

The correction captures destination bytes during initial collection and passes them into publication. The operation then compares the actual destination with that earlier value under the writer transaction. The focused gate passes 35 tests and 10 subtests, including both refusal cases and interrupted pair recovery. The wider gate passes 136 tests and 92 subtests. No server changes occur.
