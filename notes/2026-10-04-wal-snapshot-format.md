# WAL snapshot format

Date: 2026-10-04. The profile backup work reveals a limit in the native snapshot component. Default rollback-mode fixtures pass, but an actual WAL-mode database produces an image that cannot pass standalone inspection. The probe confirms header flags 2 at offsets 18 and 19. The failure is `unable to open database file`, despite committed data in the serialized image.

The [SQLite interface documentation](https://www.sqlite.org/c3ref/deserialize.html) specifies rollback flags for deserialization. The correction normalizes the copy and verifies its integrity in memory. It leaves the live connection in WAL mode. The reconstructed database includes the latest native fact committed through WAL. The combined native backup and recovery gate passes 25 tests and three subtests without skips or uncaptured warnings.
