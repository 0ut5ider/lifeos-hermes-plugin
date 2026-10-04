# Separate profile recovery and current authority

Date: 2026-10-04. Role: primary implementation and verification. The selected-profile archive now has a separate recovery path. All controls use synthetic data, actual files, SQLite, native tools, and the Hermes parser.

Recovery creates new `profile` and `native` trees. It copies archived files and metadata, reconstructs native references, and rebinds internal and native data links. It changes only the candidate ownership configuration and any recognized native connector. Ownership and sharing remain disabled. The receipt records those rebound paths. Original profiles retain later identity edits, history, facts, and forget decisions.

The first eight controls pass. The connector control then exposes an original-store reference in the copied command. Recovery now requires the known native RPC shape and binds its configuration argument to the candidate. Unknown connector programs refuse recovery before publication. The current original connector remains byte-identical.

A stronger history control uses Hermes's actual SessionDB schema and message operations. A new process opens the recovered database, reads both original messages, and appends a third. The live original database still has two messages. Native SQLite guard warnings are captured and asserted when the selected interpreter triggers them. This verifies history storage continuation; it does not claim a model conversation or an activated memory owner.

The captured-program control needs the complete native dependency boundary. Copying only TOOLS fails because MutationTier imports `../../hooks/lib/identity`. Copying the hooks then fails because the identity parser imports `yaml`. The fixture now includes the actual hooks and installed YAML package. This mirrors the profile's native program, rather than replacing its tools with a test implementation.

The intended control then fails because recovery requires the unavailable original tools despite capturing the program. Native recovery now accepts the reviewed captured tools selected by profile recovery. It creates a relative tools link that survives the final directory rename. Native fact retrieval then uses the recovered program inside the candidate profile. The original retained program directory remains intact. The focused recovery and adjacent native gate passes 18 tests and seven subtests.

A real process exits with status 73 after the candidate receipt exists and before final publication. The private stage retains disabled ownership and sharing. A fresh recovery succeeds without replacing the stage or original profile. Recovery does not start or stop services, select ownership, or import personal data. Programs and service definitions outside the archived profile still need the coordinated installation and release workflow.

The final combined gate, including recorded recovery outcomes, passes 58 tests and 24 subtests in 98.45 seconds. It includes both native and profile backup/recovery, actual command discovery, installed commands, and plugin footprint. The actual Hermes history outcome, disabled candidate receipts, and process interruption result remain in the verification directory after fixture cleanup.
