# Atlas limits review evidence

The [report](atlas-limits-review.md) reviews code commit `77615801f89bfcd63167468d1fb7dd75a9af6477` against merged main `38f5534628be21a62fea87553313b964282e8e8d`.
The implementation changes after this review have their own [verification record](../../verification/2026-10-10-atlas-limits-fixes/README.md).

The raw synthetic measurements, graphs, snapshots, experiment scripts, original fixture failures, outputs, and completion markers remain in their original formats.
The [primary verification](primary-verification/results.json) independently repeats the managed and backup experiments.

The [raw review diff](review-diff.patch.gz) uses gzip to preserve its exact patch bytes, including required context-line spaces.
The uncompressed original also remains on disk.
The [archive identity](raw-diff-archive.json) records both hashes and verifies exact decompression.
Use `gzip -dc review-diff.patch.gz` to read the diff.
The original review manifest refers to the uncompressed filename and original bytes.
