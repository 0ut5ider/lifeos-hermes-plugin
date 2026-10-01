# Rendered memory prompt review

Date: 2026-09-30
Role: Independent code reviewer
Question: Do the SOUL fingerprint and model-request checks prevent removed claims from returning through generated or cached system context, while preserving actual user-authored quotes?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The supplied 20 runtime tests and 5 real model-call tests all pass. Additional real SDK captures confirm two admission gaps and a third exposed compression-helper gap. The bounded unit is not closed.

The direct list-based cached-prompt case is correctly denied. Four alternative valid SDK request shapes send the same removed cached SOUL text. The existing compression helper fixture also sends that cached text after converting its system turn into a user-role summary request.

All findings were sent to the primary agent promptly. No implementation files were edited, no commits were made, and no live systems, accounts, SSH, actual memories, or journal tools were accessed. The only HTTP server was the supplied isolated localhost fixture.

## Finding 1: Supported iterable request shapes bypass system-text inspection

Severity: High for cached-prompt exclusion.

_prompt_text and _system_text accept lists but silently treat other collection shapes as empty. The installed OpenAI SDK accepts Iterable message collections and iterable content blocks. Its actual serializer converts tuples and generators into ordinary JSON arrays after the middleware check.

Using the supplied real host PluginContext, required middleware, SOUL loader, OpenAI SDK, and localhost server, the probe loaded stale SOUL text, refreshed the on-disk file, and admitted a fresh context. The ordinary list control produced zero HTTP requests and raised the expected model-system-prompt error. These variants each produced one successful HTTP request containing the retired system claim:

- tuple messages;
- tuple content blocks inside a system message;
- generator messages.

The resulting HTTP body has the same system-role claim as the denied list control. This is a representation gap in the new extractor, not a route or permission mismatch.

Evidence: raw/probe_sdk_shapes.py, generated sdk-*.py child programs, and raw/sdk-shapes.txt. The original model-call program was copied only into the review evidence directory; implementation and test sources were unchanged.

Recommended correction: normalize the permitted request containers once at the boundary and pass the same normalized request to the SDK, or reject unsupported shapes before transport. Do not consume a one-shot iterator for inspection while leaving an exhausted iterator for the real call. Preserve user-role quote behavior while making system/developer extraction complete.

## Finding 2: extra_body can replace the inspected messages during SDK serialization

Severity: High for effective-payload validation.

The new extractor examines top-level messages/system/instructions/input only. The installed SDK supports extra_body and merges it into the actual request body after the middleware returns.

The real fixture passed clean top-level user messages and an extra_body containing a system message with the cached retired SOUL text. Admission succeeded. The HTTP capture contains the extra_body system message, replacing the inspected clean message list, and the request completed successfully.

Evidence: raw/probe_sdk_shapes.py case extra-body, raw/sdk-extra-body.py, and the final record in raw/sdk-shapes.txt. The wire body and successful response are preserved.

Recommended correction: check the effective payload after supported SDK body merging, or reject extra_body overrides of protected instruction/message fields. It is insufficient to inspect the top-level argument while another accepted argument can replace it before transport.

## Finding 3: The exercised compression helper reclassifies cached system content as user text

Severity: Medium for the bounded helper path; full production reachability is not established here.

The existing cached-SOUL regression checks primary, sync auxiliary, and async auxiliary calls, but omits the compression operation supported by the same fixture program.

The probe invokes the original tests/memory_model_calls.py without modifying it, using run_call('compression', refresh_after_load=True). ContextCompressor._generate_summary serializes the supplied turns, including the cached system turn, into one user-role summarization prompt. _system_text sees no system/developer instruction content in that resulting SDK request. The localhost server receives one request containing the removed cached SOUL claim.

The resulting text was supplied by the host SOUL loader as a system turn. It was not an actual user-authored quote, even though the final request role is user.

Evidence: raw/probe_compression.py and raw/compression-probe.txt. The latter preserves the complete captured request. Its sole message role is user, and retired_claim_on_wire is true.

Recommended correction: preserve provenance for generated compression input or validate the governed generated input before role conversion. Do not solve this by rejecting all genuine user-role quotes. Add the existing compression operation to the cached-SOUL regression.

Scope limit: this proves the public behavior of the actual summary helper exercised by the new test program. It does not prove that a full AIAgent compression rotation supplies its protected system turn to that helper, nor that such a turn can enter a production rotation after the lifecycle checks. The requested full-rotation boundary remains open.

## Verified passing behavior

The 20 runtime tests passed in 3.453 seconds. They confirm stale on-disk SOUL refusal after forgetting, prompt hash changes invalidating retained context across restart, symlink SOUL rejection, and five ordinary system/instruction representations being denied while a genuine user-role quote is allowed. Existing authority, route, context, disabled ownership, and restart checks continue to pass.

The 5 model-call tests passed in 32.430 seconds. They use real host middleware registration, real SDK sync/async transport, actual host SOUL loading, and actual ContextCompressor._generate_summary. Allowed fixture requests reach a local HTTP server with JSON/SSE responses. Unapproved routes, changed authors, and resumed invalidated context produce no additional admitted request in the tested cases. Cached SOUL is denied for the three list-based primary/auxiliary cases included in the regression.

The new _rendered_prompt path checks that SOUL is a regular file owned by the current UID, reads and fingerprints it, and applies exact retained-claim filtering with the current timestamp. Using current time avoids rejecting an otherwise unchanged public constitution solely because it predates an unrelated correction. Its fingerprint participates in the existing generation stamp.

## Test claim limits

The program's primary operation is an explicit required-middleware call around OpenAI.chat.completions.create. It is not a complete AIAgent invocation. Compression exercises the actual summary helper and SDK path, not a full conversation rotation. The admitted private marker in positive requests is synthetic text placed in the fixture request; those tests do not demonstrate retrieval of a real private fact into a full agent prompt.

No complete model-routing inventory, output-destination review, activation gate, or lifecycle closure follows from these results. Actual user-authored quotes intentionally remain permitted. The findings concern generated system material, accepted SDK container shapes, and effective-body overrides.

## Evidence and reproducibility

Interpreter: /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

Prepared host source: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources-fixed/hermes.

Native fixture: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources-fixed/lifeos/LifeOS/install.

raw/commands.txt contains exact commands and environment paths. raw/runtime.txt and raw/model_calls.txt contain complete successful test outputs. Initial source snapshots and initial/final hashes are saved in raw/. Prepared host file hashes are recorded separately. The primary agent's supplied before-fix characterization logs were copied with a primary- prefix; these are preserved provenance, not independent results from this review.

The SDK probe preserves its denied control, successful bypass bodies, stdout, and stderr. Expected denial tracebacks in raw output are part of the reproduction. Raw source and upstream output are kept exactly, including their original punctuation. Authored report prose contains no em dash.

## Next review

Fix and rerun the SDK shape and extra_body cases before claiming that the actual model system payload is checked. Resolve or explicitly constrain the demonstrated compression-helper behavior without conflating generated input with genuine user quotes. Preserve the stated full-agent, rotation, route inventory, activation, and output-destination limits in the closure report.
