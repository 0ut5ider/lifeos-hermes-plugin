# LifeOS 0.4.2 stable release qualification

The candidate preserves the reviewed rc.3 program behavior and fixed native inputs. Its stable version creates a distinct package identity. Qualification binds all evidence to that package.

The authorized work completes six gates: freeze the candidate, verify manager-free web installation and synthetic memory ownership, verify installed update and recovery, qualify development .252, verify off-server whole-guest recovery, and publish stable assets with public latest-stable acceptance.

Daily .253 stays on accepted 0.3.1. No personal data is imported or reset. Existing release assets remain immutable. Voice, media processing, the Pulse core-file editor, and migration remain deferred.

PROGRESS.json records measured results. An incomplete gate does not qualify publication.

The first package at `742a0c33` remains unpublished. Clean ownership activation found that the detached worker inherits a shared-write file mask. The corrected worker sets a private mask before it creates native installation state.

The corrected package at `87205092` passes 675 integration tests and 716 native tests. Its archive SHA-256 is `76c1c10e82ce75f86858a2cd27ae609f5f7eb8a8bc79612d94df6f95f45136a4`. The [candidate receipts](candidate-87205092/) retain the exact package identities and actual operation outcomes.

Clean guest 109 installs the manager from the default GitHub URL without Force reinstall. Its complete installation, governed ownership activation, and actual Hermes save and recall pass. Development guest 101 passes update, program rollback, actual worker interruption, and installed recovery. The final development operation, reboot, whole-guest restoration, and public stable replay remain incomplete at this checkpoint.
