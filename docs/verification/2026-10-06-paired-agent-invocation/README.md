# Agent invocation model evidence

Date: 2026-10-06. Target: the isolated development container at 192.168.8.252.

Two real Claude Code 2.1.272 and Hermes cases now record equal inherited and explicit Opus dispatch state. All four clients pass. The fixtures require the general-purpose agent type. They preserve model, level, type, and parent session identity in the comparison. Only timestamps, paths, identifiers, and model-authored descriptions and prompt previews are normalized.

The inherited case exposed two concrete differences. Claude Code writes the assistant tool call before PreToolUse. Hermes writes it later. The request alias also differs from the served model. The bridge now observes the successful API response and supplies its served model in a bridge-owned `hermes_runtime` field. Tool arguments cannot supply that field. The native hook keeps explicit dispatch precedence and its native transcript fallback.

The native regression verifies start and completion correlation, removal of the start record, explicit-tier precedence, invalid metadata, and the native transcript fallback. The focused suite passes 298 tests, with one optional environment-dependent test skipped. Earlier runs with an incomplete Python environment failed. The final run uses the existing complete test environment.

The live cases cover PreToolUse.3.2. They do not establish complete agent lifecycle compatibility. Background completion, concurrent dispatches, and full installed groups remain separate checks. The existing PostToolUse case remains unchanged. Production and Discord remain on .212.

The source manifest records hashes for the tested working tree. Raw private model requests stay outside Git. The collector checks their hashes and all successful HTTP responses before it exports the public artifacts.
