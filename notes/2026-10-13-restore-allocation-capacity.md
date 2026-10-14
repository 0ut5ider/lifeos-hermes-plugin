# Restore capacity after filesystem allocation

2026-10-13. The 300 GiB disposable restore fails at 91% while extracting `libpython3.14.so.1.0`. Proxmox reports error 28, no space left on device, and removes the failed guest and image. The host still has about 660 GiB available. The completed PBS backup remains intact.

An empty filesystem with the exact Proxmox ext4 formatting options provides 279.227 GiB usable for the unprivileged extractor. Its 19,660,788 free inodes exceed the catalogue's 12,922,340 separate inode entries. The catalogue contains 11,234,667 regular files, 1,560,292 directories, and 5,819,997 hardlink entries. Regular-file sizes require 297.764 GiB after 4 KiB allocation rounding. Directories require at least another 5.952 GiB. File blocks alone exceed the available capacity. This proves a restore filesystem block limit, rather than a host storage or inode limit.

The first catalogue collector captures no stdout records because this client writes its catalogue to stderr. A corrected streaming parser counts metadata without exporting paths. Its complete parse has zero errors. The protected temporary raw catalogue is removed after the aggregate receipt is saved.

The retry uses the same protected backup with a 400 GiB disposable filesystem. The same formatter provides 372.650 GiB usable and 26,214,388 free inodes. That leaves 68.934 GiB above the measured file allocation and minimum directory storage. The failed workflow and its successful backup steps remain retained. The retry is still running at this checkpoint. Product code, daily programs, and personal data stay unchanged.

The [measured cause receipt](../docs/verification/2026-10-13-release-0.4.2/candidate-87205092/restore-capacity-cause.json) records the counts and capacity. Release publication still requires the completed retry and all actual verification steps.
