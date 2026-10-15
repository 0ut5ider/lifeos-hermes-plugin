# Account for generated plugin bytecode during backup

Date: 2026-10-15.

The actual `.244` browser activation at checkpoint `89f26d06` stops during profile backup. The failure occurs before any provider change. Read-only instrumentation identifies `plugins/lifeos-release-manager/__pycache__`: its owner and physical path are correct, but its mode is 0775. The strict backup directory check refuses shared write access.

The detached worker uses isolated Python. Its environment variable for bytecode writes does not disable writes under isolation, and the user manager supplies its default umask. The worker can create a generated cache before `load_bridge` disables writes. The launch now passes `-B`, sets the worker flag before importing manager modules, and requests umask 0077 from systemd.

Profile backups now record plugin `__pycache__` directories as regenerable exclusions. They retain plugin source and workspace files, including a same-named workspace directory. The original cache-permission reproduction fails before the correction. The cache and related workflow controls pass nine tests afterward.

The installed failure leaves the dashboard stopped. The operator authenticates through the actual dashboard password provider, obtains the normal exact recovery grant, and cancels the failed preparation. The dashboard resumes. A separate actual-service regression reproduces the failure recovery gap. Preparation now resumes its original services after an ordinary exception when ownership has not changed. Hard process exits retain durable recovery state. No personal data is restored or reset.
