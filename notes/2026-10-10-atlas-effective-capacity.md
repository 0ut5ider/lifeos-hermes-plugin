# Atlas capacity is governed by more than database bytes

Date: 2026-10-10

The first limit review finds a lower bound than the two MiB database cap. An actual 110-asset fixture admits 9,996 projected text fields at 402 retained collector runs. The next two runs produce 10,026 fields, publish the graph, and fail the reader admission check. The database is only 131,072 bytes. Raising the database cap does not address this failure.

Independent managed, freshness, and backup repetitions pass with empty stderr. They reproduce exact grouped recovery, unchanged narrative metrics after an unsynchronized source edit, and omitted Atlas history in native profile recovery. The implementation must admit planned state before publication. Daily refresh uses the current owner command. The final guest recovery gate must restore external Atlas state together with sources, cache, governance receipts, and journals.
