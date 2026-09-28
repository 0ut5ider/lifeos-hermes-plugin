# Live SSH file path probe

Date: 2026-09-28. Both client and SSH target were isolated accounts on `.212`; no production host was used. A disposable remote account and key were created for this probe. The client used a synthetic `HERMES_HOME` under `/tmp` so its normal Hermes profile was not copied to the remote account.

Hermes's SSH backend connected to the remote account and read `proof.txt` through `read_file_tool`. It returned `remote-proof`. A second call used `write_file_tool` to create `lifeos-remote-hook-proof.txt`; `read_file_tool` then returned its content. For the relative write path, Hermes's `_resolve_path_for_task` and the bridge's `_hook_file_path` both returned `/home/lifeos-remote-probe/workspace/lifeos-remote-hook-proof.txt`.

This verifies a live SSH file target and hook path translation. It does not establish native hook effect parity for remote files. The native LifeOS hooks still run on the Hermes host, and hooks that read a file by `file_path` need access to the target filesystem. Container operations remain untested. The remote account and key are test artifacts outside Git and must be removed when this branch of the investigation ends.
