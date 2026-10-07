# Standalone SQLite backup images

Date: 2026-10-04. The [gate](gate.txt) passes 25 tests and three subtests without skips, failures, or uncaptured warnings. The [command](command.json) retains the environment and source hashes. The [completion marker](gate.done) records exit status 0.

The [initial probe](before.txt) puts the actual native governance database into write-ahead logging (WAL) mode. It then commits another native fact. The serialized image retains format flags 2 at offsets 18 and 19. Standalone inspection fails with `unable to open database file`.

SQLite documents that deserialization requires rollback flags for a WAL image. The snapshot helper changes only those two bytes in the serialized copy and checks its integrity in memory. It preserves the source connection and journal mode. See the [SQLite deserialization interface](https://www.sqlite.org/c3ref/deserialize.html).

The passing control verifies format flags 1 in the snapshot, reconstruction of the newly committed fact, and WAL mode on the original connection. Native backup creation, separate recovery, and actual Hermes command discovery also pass. This component changes no schema or dependency and makes no server changes.
