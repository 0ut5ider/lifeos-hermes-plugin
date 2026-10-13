# ZFS unmount during release qualification

2026-10-13. The stable 0.4.2 qualification starts by stopping CT106 and restoring its stock Hermes snapshot. Stop completes. The controller times out after 120 seconds during rollback. The original Proxmox operation keeps running; no duplicate rollback is submitted.

The measured wait occurs in `zfs unmount rpool/data/subvol-106-disk-0`. The unmount stack waits in `zfs_preumount` and `taskq_wait_outstanding`. A `z_zrele` thread waits in `folio_wait_bit_common` during `truncate_inode_pages_range` and `zpl_evict_inode`. This identifies the waiting subsystem. It does not establish the underlying defect.

The host has about 96 GiB available memory. The rpool has 715 GiB free and continues to serve I/O. Memory exhaustion and a full pool do not explain this observation. A fresh disposable CT107 is provisioned from the existing Ubuntu template for the manager-free installation test. Existing application guests remain outside that provisioning action. The failed CT106 reset stays as evidence.

The CT107 provisioning helper incorrectly inherits the operator's private mask 077. Proxmox creates root-owned mode 0700 staging directories. The actual task log reports `tar: /var/lib/lxc/107/rootfs: Cannot open: Permission denied`. Its cleanup then waits in another ZFS unmount. The earlier October 11 measured namespace probe already documents this boundary for backup and restore. The corrected CT108 trial sets mask 022 only in the Proxmox create child and keeps operator evidence private. This correction does not establish a cause for the original CT106 kernel wait.
