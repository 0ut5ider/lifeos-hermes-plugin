# Daily guest installation

Date: 2026-10-11. Adrian authorizes a new daily guest and release installation.

The daily guest is `lifeos-daily`, unprivileged Proxmox container `102`, on `pve-tr1950x` at `192.168.8.101`. Its address is `192.168.8.253/24`, its gateway is `192.168.8.1`, and its timezone is `America/Toronto`. It uses Ubuntu 24.04, four CPU cores, eight GiB of memory, and an 80 GiB root disk on `local-zfs`. The guest has no additional mounted data disks. The existing processing VM and development container remain unchanged.

Key-based SSH accepts the operator key for `lifeos-hermes` and `root`. The operator verifies the guest host key through Proxmox before adding it to known hosts. The account home is `/home/lifeos-hermes`. The selected LifeOS home and data paths are in [installation.json](installation.json). The selected Hermes profile is `/home/lifeos-hermes/.hermes`.

The installation uses the certified version 0.2.0 program archive at `11577ed4` and the compiled Hermes dashboard companion. Main commit `2514eea8` contains the same program bytes. The installation copies the tested Python 3.14.7 environment, Bun 1.3.14, and Node 26.7.0 runtime. It preserves the private FlashNext model and the four approved tier efforts. It copies only the model credential. It excludes Discord credentials and all existing personal data.

The installer prepares a fresh Adrian and Cerebo store with zero active facts. It empties 54 personal template files and omits three sample files. It initializes an empty Atlas graph. The brief returns `Good morning.` The installer retains native templates outside active USER data. Ownership and sharing remain disabled.

The Hermes dashboard runs on loopback port 18819 with password authentication. The declared public URL engages the native authentication gate. Pulse uses loopback port 18837 when activated. The gateway and Pulse service definitions are installed but remain inactive until the channel and recovery gates pass. The separate Telos application, media runner, and Pulse core-file editor remain excluded.

The initial program extraction incorrectly strips one directory component. The operator retains that attempt and extracts the archive correctly. A later source validation rejects the compiled dashboard overlay in the sealed Hermes source. The corrected installation keeps sealed source and the dashboard runtime copy separate. A dashboard probe then identifies native local token mode for the loopback public URL. The operator declares the daily address, restarts the dashboard, and repeats authenticated checks. No native application code changes for these corrections.

The configured Proxmox backup job is `lifeos-daily-offserver`. It backs up container 102 to `PBS-01`, server `192.168.8.24`, datastore `PlutoNAS_Backup`. It uses stop mode and retains seven daily, four weekly, and three monthly backups. Its calendar is 01:00 in the Proxmox host timezone, which currently reports `EST -0500`. This is 02:00 in the daily guest's current Toronto daylight time. The operator does not change the host timezone or existing backup jobs.

Whole-guest recovery acceptance and final Discord channel admission remain in progress. Installation alone does not establish daily Discord readiness. The development bot remains on `.252` until the final channel check and cutover.
