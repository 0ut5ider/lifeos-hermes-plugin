# Optional SSH memory sharing component

This component lets another agent reach the LifeOS memory service through a restricted SSH key. It is separate from the `lifeos_hook_bridge` plugin package. The plugin installs and runs without it.

The component changes the SSH authorized keys file of the account that runs Hermes. Each enrollment adds one `restrict,command=` entry that can only start the memory process for one named client. Install the component only if you want that capability.

## Install

Run this command as the account that runs Hermes:

```sh
python3 optional/lifeos-memory-sharing/install.py --hermes-home ~/.hermes
```

The installer copies `memory_sharing.py` to `~/.hermes/lifeos-memory-sharing/` with owner-only permissions. Reload the LifeOS dashboard page afterward. The **Share memory with another agent** section then shows the connection form.

The plugin loads the component only when all of these conditions are true:

- The directory and the file are physical files that the Hermes account owns.
- Neither has group or world write access.
- The file hash equals the hash that this plugin release records.

A plugin update that changes the recorded hash requires a new run of the installer.

## Remove

```sh
python3 optional/lifeos-memory-sharing/install.py --hermes-home ~/.hermes --remove
```

Removal deletes the installed program. It does not change connection grants or SSH entries. Revoke each connection in the dashboard before you remove the component. Without the component, the dashboard can still disable a connection grant, and a disabled grant refuses every request. The SSH entry of that connection then stays in the keys file. The dashboard marks such a connection. After you reinstall the component, the dashboard offers **Remove SSH entry** for it.
