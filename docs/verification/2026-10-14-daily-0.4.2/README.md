# Daily promotion and native HOME compatibility

Adrian authorizes promotion of the qualified release, preservation of personal data and models, live Cerebo acceptance, and automatic morning observation.

The daily server stays on accepted 0.3.1. The fresh prepromotion backup is `PBS-01:backup/ct/102/2026-10-14T12:48:53Z`. Both this backup and the previously verified October 12 checkpoint are protected from pruning. All three daily services resume after the backup.

The native Plugins page installs the published release manager. All 19 installed source files match the exact qualified 0.4.2 archive. The existing dashboard requires a restart to load its backend routes. The authenticated owner is `adrian` through the existing BasicAuth provider.

Actual preparation of 0.4.2 fails before it selects programs. Operation `b4eefd2e224c4922af888f8b10a7b54d` retains its failure metadata. The failure is in release_plan.inspect_operation at the account launcher boundary. All three application services use the private native fresh-store directory as HOME. Their launchers belong to `/home/lifeos-hermes`, which also owns the `.hermes` profile. The manager incorrectly treats service HOME as the launcher account boundary.

Candidate 0.4.3 corrects this account binding. It resolves standard and named profile accounts from their physical profile paths and preserves explicit HOME for custom profiles. It requires current owner directories without aliases or shared-write permissions. Preparation children use the account context; existing application service HOME values remain unchanged.

The new account regressions and existing command, preparation, and service checks pass with the pinned Python runtime and qualified Hermes source. Initial system-Python runs lack the required pinned modules and are not acceptance results. The candidate still requires packaged integration qualification and a service-backed rehearsal of the actual daily layout before deployment. Published 0.4.2 assets remain immutable. No personal data is imported or reset.
