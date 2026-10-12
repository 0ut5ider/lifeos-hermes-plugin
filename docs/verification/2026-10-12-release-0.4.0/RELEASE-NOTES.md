LifeOS 0.4.0 adds complete installation and updates through Hermes.
The release manager prepares the package before it changes the active installation.
The authenticated dashboard lets the owner review and start the update.
The worker coordinates programs, native configuration, public commands, and service restarts.
Recovery and rollback preserve user data and refuse conflicting program changes.

The package uses Hermes v0.21.7 at commit 71d34bad1045610252eda02ee79549436896e784.
The package contains ten Hermes patch groups and twenty-five LifeOS patch groups.
The package preserves the model and tier mapping.
The package includes the frozen Python dependencies and Hermes dashboard.

The release certificate identifies the exact program archive and qualification results.
The immutable candidate manifest records build-time state.
The certificate records release qualification after the checks pass.

For installation, install and enable the standalone manager from this release tag.
Then run `hermes lifeos-release prepare --version 0.4.0 --name Adrian --assistant Cerebo`.
Review the operation in the authenticated Hermes dashboard before you start it.
An existing installation with managed memory requires an owner grant for its native mount.
Installation does not activate lasting memory automatically.

The 0.3.1 release assets remain historical release and rollback inputs.
The release manager requires the new frozen dependency closure.
The release manager does not install the historical 0.3.1 archive.
Install the manager from the qualified tag before using an older coordinator.

Voice, media processing, data migration, and the Pulse core-file editor remain deferred.
