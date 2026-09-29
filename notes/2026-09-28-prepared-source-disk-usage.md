# Prepared source disk usage

Date: 2026-09-28. The `.212` source preparation check failed with `Disk quota exceeded` while cloning Hermes. The two prepared trees left from earlier checks each used 5.7 GB in `/tmp`. The source checkout's `.git` directory alone used 5.4 GB. At failure, `/tmp` had 6.8 GB free on a 32 GB filesystem, which was insufficient for the test's additional full clone.

Removing only the two generated prepared trees raised `/tmp` free space to 18 GB. The unchanged suite then passed: 302 tests, 55 optional skips. The failure was environmental, not a patch conflict. This matters for clean installs: the current source preparer makes an independent full clone and needs several gigabytes of headroom for each concurrent run. A future preparer could use a shared object store, but that would make a prepared tree dependent on the source repository. That tradeoff needs an explicit design and a deletion test before changing the clone mode.
