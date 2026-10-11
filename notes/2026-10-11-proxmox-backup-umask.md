# Proxmox backup staging and the inherited file mask

2026-10-11, `pve-tr1950x`, Proxmox 9.2.21. The first cold PBS backup of unprivileged container 102 fails before data upload. The mapped backup process reports permission denied for `/var/tmp/vzdumptmp3439828_102/etc/vzdump/pct.conf`. The operator controller uses `umask 077` for private evidence and passes that mask to `vzdump`.

The installed Proxmox code creates its staging directory with a plain `mkdir`. The LXC backup then invokes `proxmox-backup-client` through `lxc-usernsexec` with container root mapped to host UID 100000. The staging directory belongs to host root. A mask of 077 produces mode 0700, so the mapped backup process cannot traverse it.

A controlled filesystem probe uses the same namespace mapping. At mask 077, the parent mode is 0700, the file mode is 0600, and the readability check exits 1. At mask 022, the parent mode is 0755, the file mode is 0644, and the check exits 0. The correction sets mask 022 only for the `vzdump` child process. Operator evidence remains private. The controller retries the same retained synthetic baseline. No Proxmox library, backup credential, existing backup job, or application program changes.

The [failed backup output](../docs/verification/2026-10-11-daily-guest/backup-first.stdout) remains retained. A successful retry must still complete upload and a real restore. The permission probe alone does not prove recoverability.

The interrupted-case restore exposes the same inherited-mask requirement for `pct restore`. Container 104's staging directory is root-owned mode 0700, and the mapped root cannot traverse it. A direct directory probe produces mapped-root exit 1 at mode 0700 and exit 0 at mode 0755. The operator applies child umask 022 to both `vzdump` and `pct restore`. Private operator evidence remains mode 0700/0600. The failed restore removes its target volume and configuration; the operator confirms that only an empty rootfs directory remains and sets the staging parent to mode 0755 before repeating the restore.
