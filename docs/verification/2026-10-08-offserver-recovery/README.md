# Off-server container recovery

Date: 2026-10-08. This check uses the authorized disposable installation container on Proxmox `.101`. It does not change VM `801` or the source container.

The configured `PBS-01` storage points to Proxmox Backup Server at `192.168.8.24`, datastore `PlutoNAS_Backup`. The [backup log](ct100-backup.log) records a successful snapshot backup of container `100` to `ct/100/2026-10-08T16:10:54Z`. The [restore log](ct102-restore.log) records a successful restore to new container `102`. Both completion markers contain zero.

The restored container receives a unique network address. The operator disables its network link and automatic boot before starting it. The restored account cannot contact model services or Discord. The container hostname is `lifeos-recovery-probe`. This container is a recovery fixture, not the daily server.

The [comparison](file-comparison.json) verifies seven selected file hashes across the original and restored installation. These files include Hermes configuration, identity, native memory configuration, plugin source, Hermes source, and both native hot memory files. The restored SQLite history contains the same eight sessions and 22 messages. The database comparison uses row counts and does not export message content. The restored guest boots successfully with its network link down.

The backup destination is another server address. This check does not establish independent physical hardware or storage failure domains. It also does not verify the final daily candidate or automatic scheduled backups. A separate development-profile snapshot and recovery check retains coherent application backup evidence.
