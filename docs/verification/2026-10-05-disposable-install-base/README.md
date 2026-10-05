# Disposable installation test guest

Date: 2026-10-05. Adrian authorizes disposable guests on `root@192.168.8.101`, with the existing VM preserved. SSH key access succeeds. The primary creates unprivileged CT `100` from the host's Ubuntu 24.04 template catalog.

| Setting | Selected value |
| --- | --- |
| Host | Proxmox `192.168.8.101` |
| Container | `100`, `lifeos-install-probe` |
| Operating system | Ubuntu 24.04 LTS |
| CPU | 2 cores, limit 2, weight 50 |
| Memory | 4,096 MiB, no swap |
| Root disk | 24 GiB on `local-zfs` |
| Network | DHCP on `vmbr0`; observed address `192.168.8.245` |
| Features | Unprivileged container, nesting enabled |
| Automatic boot | Disabled |
| Baseline snapshot | `stock-os`, before Hermes installation |

[create.py](create.py) records the commands used to download the template, create the guest, and start it. [create-output.txt](create-output.txt) retains their raw output. [base-checks.json](base-checks.json) verifies the operating system, network address, running systemd, and container configuration. [preservation.json](preservation.json) records the baseline snapshot and equal before/after configuration hashes for the running VM `801`. Its memory setting remains 102,400 MiB.

The host reports 125 GiB of RAM and approximately 110 GiB available before guest creation. The primary makes no change to VM `801`, its devices, host networking, or agent settings. The host emits an existing TrueNAS storage API warning during these commands; the commands succeed. This record does not investigate that unrelated warning.

Use `pct exec 100 -- <command>` through the authorized host SSH connection for guest access. No agent credentials or personal data are installed in this base fixture. Stock Hermes admission, complete installation, two-release updates, interruption, and rollback remain unverified.

After the tests, remove only this owned guest with `pct shutdown 100`, then `pct destroy 100`. Confirm the name and ownership description first. The downloaded Ubuntu template remains cached in host storage. Guest destruction removes its root disk and snapshots; it does not change VM `801`.
